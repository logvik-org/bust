"""Saving a register map (`bust FILE -a`, the editor's save) must be lossless.

The JSON written by Module.to_json has to parse back into a module that generates
byte-identical output, and a bust 1.0 file has to keep its access-mode keys
instead of collapsing to the legacy `mode` schema."""

import json
import os

import pytest

from bust.core.bus import Bus
from bust.core.field import INHERITABLE_ACCESS
from bust.core.module import Module
from bust.generation import _ENDPOINT_GENERATORS, _TESTBENCH_GENERATORS
from bust.generators.documentation_generator import DocumentationGenerator
from bust.generators.factory import GeneratorFactory
from bust.generators.header_generator import HeaderGenerator
from bust.settings import Settings
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLES = [
    "example_prototype.json",
    "example_axi.json",
    "example_ipbus.json",
    "example_access_matrix.json",
]
_NEW_SCHEMA_KEYS = (*INHERITABLE_ACCESS, "position", "enums")


def _example_path(name):
    return os.path.join(_REPO_ROOT, "example", name)


def _build_module(json_file, config):
    settings = Settings(json_file, config["settings"])
    return Module(config["module"], Bus(config["bus"]), settings)


def _save_and_reload(json_file):
    """What `bust FILE -a` does, followed by parsing the saved file again.

    Returns the module as saved, the saved JSON text, and the reloaded module.
    """
    saved_module = _build_module(json_file, json_parser(json_file))
    saved_module.update_addresses()
    saved_json = saved_module.to_json(True)
    return saved_module, saved_json, _build_module(json_file, json.loads(saved_json))


def _generated_artifacts(module):
    bus_type = module.bus.bus_type
    header = HeaderGenerator(module)
    artifacts = {
        "localbus_pkg": GeneratorFactory.generate_localbus_package_vhdl(module),
        "regfile_pkg": GeneratorFactory.generate_regfile_package_vhdl(module),
        "regfile": GeneratorFactory.generate_regfile_vhdl(module),
        "endpoint": _ENDPOINT_GENERATORS[bus_type](module),
        "top": GeneratorFactory.generate_module_top_vhdl(module),
        "testbench": _TESTBENCH_GENERATORS[bus_type](module),
        "c_header": header.generate_c_header(),
        "cpp_header": header.generate_cpp_header(),
        "python_header": header.generate_python_header(),
    }
    if bus_type == "ipbus":
        artifacts["ipbus_xml"] = header.generate_ipbus_addr_table()
    return artifacts


def _without_addresses(module_cfg):
    registers = [
        {key: value for key, value in reg.items() if key != "address"}
        for reg in module_cfg["register"]
    ]
    return dict(module_cfg, register=registers)


def _new_schema_keys(module_cfg):
    """(register, field, key) for every bust 1.0 key; field is None at register level."""
    found = []
    for reg in module_cfg["register"]:
        found += [(reg["name"], None, key) for key in _NEW_SCHEMA_KEYS if key in reg]
        for field in reg.get("fields", []):
            found += [
                (reg["name"], field["name"], key)
                for key in _NEW_SCHEMA_KEYS
                if key in field
            ]
    return found


@pytest.mark.parametrize("example", _EXAMPLES)
def test_saved_json_regenerates_identical_output(example):
    saved_module, saved_json, reloaded = _save_and_reload(_example_path(example))

    expected = _generated_artifacts(saved_module)
    actual = _generated_artifacts(reloaded)
    assert actual.keys() == expected.keys()
    for name, text in expected.items():
        assert actual[name] == text, name
    assert reloaded.to_json(True) == saved_json


@pytest.mark.parametrize("example", _EXAMPLES)
def test_saved_json_regenerates_identical_doc(example):
    pytest.importorskip("pylatexenc")
    saved_module, _, reloaded = _save_and_reload(_example_path(example))

    assert DocumentationGenerator(reloaded).generate_tex_documentation(
        "1.0.0-dev"
    ) == DocumentationGenerator(saved_module).generate_tex_documentation("1.0.0-dev")


@pytest.mark.parametrize("example", _EXAMPLES)
def test_saved_json_keeps_every_authored_key(example):
    """Saving only (re)numbers addresses; the rest of the module is as written."""
    path = _example_path(example)
    _, saved_json, _ = _save_and_reload(path)

    saved = json.loads(saved_json)["module"]
    assert _without_addresses(saved) == _without_addresses(json_parser(path)["module"])


def test_saved_new_format_file_stays_new_format():
    path = _example_path("example_prototype.json")
    _, saved_json, _ = _save_and_reload(path)

    saved = json.loads(saved_json)["module"]
    authored_keys = _new_schema_keys(json_parser(path)["module"])
    assert authored_keys
    assert _new_schema_keys(saved) == authored_keys
    assert all("mode" not in reg for reg in saved["register"])


def test_save_keeps_field_level_access_without_register_defaults():
    """Fields that carry their own sw/hw under a register with no access keys
    must not gain a legacy `mode` on save, and module/settings options survive."""
    fields = [
        {"name": "ready", "type": "bit", "sw": "ro", "hw": "w"},
        {
            "name": "count",
            "type": "vector",
            "width": 4,
            "position": 8,
            "sw": "ro",
            "hw": "w",
            "we": True,
        },
    ]
    cfg = {
        "name": "m",
        "byte_addressable": False,
        "register": [{"name": "status", "type": "fields", "fields": fields}],
    }
    bus = Bus({"type": "axi", "addr_width": 32, "data_width": 32})
    settings = Settings(os.path.join("cfg", "m.json"), {"proj_dir": "out"})

    saved = json.loads(Module(cfg, bus, settings).to_json(True))

    assert saved["settings"]["proj_dir"] == "out"
    assert saved["module"]["byte_addressable"] is False
    (status,) = saved["module"]["register"]
    assert "mode" not in status and "sw" not in status
    assert status["fields"] == fields
