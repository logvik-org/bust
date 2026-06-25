"""Verify the generated local-bus regfile package.

Two guards: a golden-file comparison against the committed reference (regression),
and a structural comparison against the hand-written, simulation-verified prototype
package in `hdl/prototype/` (the generator must reproduce the verified HDL)."""

import json
import os
import re

from bust.core.bus import Bus
from bust.core.module import Module
from bust.generators.factory import GeneratorFactory
from bust.generation import generate_output
from bust.settings import Settings
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLE = os.path.join(_REPO_ROOT, "example", "example_prototype.json")
_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_regfile_pkg.vhd"
)
_PROTOTYPE = os.path.join(_REPO_ROOT, "hdl", "prototype", "prototype_regfile_pkg.vhd")
_ENTITY_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_regfile.vhd"
)
_AXI_ENDPOINT_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_axi_endpoint.vhd"
)
_IPB_ENDPOINT_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_ipb_endpoint.vhd"
)
_MODULE_TOP_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype.vhd"
)


def _build_module():
    with open(_EXAMPLE) as fp:
        cfg = json.load(fp)
    return Module(cfg["module"], Bus(cfg["bus"]), settings=None)


def _structural_lines(text):
    """Declaration lines with comments, blanks, and whitespace normalized away.

    Reset-aggregate and is_mapped lines are dropped: the verified prototype and the
    generator express the same values differently (`(others => '1')` vs `4X"F"`,
    wrapped vs single-line boolean), which is functional, not structural. Enum
    decode `when ... =>` arms are kept so the generated conversion logic is
    checked."""
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"--.*$", "", raw).strip()
        line = re.sub(r"\s+", " ", line)
        is_reset_aggregate = "=>" in line and not line.startswith("when")
        if not line or is_reset_aggregate or re.match(r"(return |or )?sel_is", line):
            continue
        lines.append(line)
    return lines


def test_regfile_package_matches_golden():
    generated = GeneratorFactory.generate_regfile_package_vhdl(_build_module())
    with open(_GOLDEN) as fp:
        assert generated == fp.read()


def test_regfile_package_matches_verified_prototype():
    generated = GeneratorFactory.generate_regfile_package_vhdl(_build_module())
    with open(_PROTOTYPE) as fp:
        assert _structural_lines(generated) == _structural_lines(fp.read())


def test_regfile_entity_matches_golden():
    generated = GeneratorFactory.generate_regfile_vhdl(_build_module())
    with open(_ENTITY_GOLDEN) as fp:
        assert generated == fp.read()


def test_axi_endpoint_matches_golden():
    generated = GeneratorFactory.generate_axi_endpoint_vhdl(_build_module())
    with open(_AXI_ENDPOINT_GOLDEN) as fp:
        assert generated == fp.read()


def test_ipb_endpoint_matches_golden():
    generated = GeneratorFactory.generate_ipb_endpoint_vhdl(_build_module())
    with open(_IPB_ENDPOINT_GOLDEN) as fp:
        assert generated == fp.read()


def test_module_top_matches_golden():
    generated = GeneratorFactory.generate_module_top_vhdl(_build_module())
    with open(_MODULE_TOP_GOLDEN) as fp:
        assert generated == fp.read()


def _one_register_module(bus):
    return Module(
        {"name": "m", "register": [{"name": "r", "type": "default", "mode": "rw"}]},
        bus,
        settings=None,
    )


def test_module_top_instantiates_axi_endpoint():
    out = GeneratorFactory.generate_module_top_vhdl(_one_register_module(_axi_bus()))
    assert "entity m is" in out
    assert "i_endpoint : entity work.m_axi_endpoint" in out
    assert "awaddr" in out and "rready" in out


def test_module_top_instantiates_ipb_endpoint():
    bus = Bus(
        {"type": "ipbus", "addr_width": 32, "data_width": 32, "comp_library": "bust"}
    )
    out = GeneratorFactory.generate_module_top_vhdl(_one_register_module(bus))
    assert "entity m is" in out
    assert "i_endpoint : entity work.m_ipb_endpoint" in out
    assert "ipb_in" in out and "ipb_out" in out
    assert "use ipbus.ipbus.all;" in out


def _axi_bus():
    return Bus(
        {"type": "axi", "addr_width": 32, "data_width": 32, "comp_library": "bust"}
    )


def test_constant_only_module_omits_empty_record_families():
    """A field that holds no state and is not hw-driven must not produce empty
    storage / from_hw records (an empty VHDL record is illegal)."""
    reg = {
        "name": "stat",
        "sw": "ro",
        "hw": "r",
        "type": "fields",
        "fields": [{"name": "id", "type": "vector", "width": 8}],
    }
    module = Module({"name": "ronly", "register": [reg]}, _axi_bus(), settings=None)
    out = GeneratorFactory.generate_regfile_package_vhdl(module)

    assert not re.search(r"is record\s+end record", out)
    assert "type t_ronly_regs is record" not in out
    assert "C_RONLY_REGS_RESET" not in out
    assert "type t_ronly_from_hw is record" not in out
    assert "type t_ronly_to_hw is record" in out
    assert "return sel_is(sel, C_ADDR_STAT);" in out


def test_constant_only_entity_uses_literals_not_regs():
    """The entity must not reference the `regs` signal for a module whose fields
    hold no state (the storage record is omitted); reads/outputs use the constant."""
    reg = {
        "name": "stat",
        "sw": "ro",
        "hw": "r",
        "type": "fields",
        "fields": [{"name": "id", "type": "vector", "width": 8, "reset": "0xAB"}],
    }
    module = Module({"name": "ronly", "register": [reg]}, _axi_bus(), settings=None)
    out = GeneratorFactory.generate_regfile_vhdl(module)

    assert "signal regs " not in out
    assert "regs." not in out
    assert 'rdata(7 downto 0) <= 8X"AB";' in out
    assert 'to_hw.stat <= (id => 8X"AB");' in out


def test_non_fields_registers_normalize_to_implicit_field():
    """A bit/vector/default register stands for one full-width field named after
    it, so the field-based regfile generator works on legacy register maps."""
    registers = [
        {"name": "flag", "type": "bit", "mode": "rw"},
        {"name": "word", "type": "vector", "width": 12, "mode": "rw"},
        {"name": "whole", "type": "default", "mode": "rw"},
    ]
    module = Module(
        {"name": "legacy", "register": registers}, _axi_bus(), settings=None
    )

    flag, word, whole = module.registers
    assert flag.fields == []  # legacy generator still sees no fields
    assert [f.name for f in flag.effective_fields] == ["flag"]
    assert [f.name for f in word.effective_fields] == ["word"]
    assert [f.name for f in whole.effective_fields] == ["whole"]

    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "field0" not in pkg
    assert "flag : std_logic;" in pkg
    assert "word : std_logic_vector(11 downto 0);" in pkg
    # default register spans the full module data width (32).
    assert "whole : std_logic_vector(31 downto 0);" in pkg
    # The whole stack generates without referencing a non-existent member.
    GeneratorFactory.generate_regfile_vhdl(module)
    GeneratorFactory.generate_axi_endpoint_vhdl(module)


def _generate_only_localbus(out_dir, gen_localbus):
    cfg_path = os.path.join(_REPO_ROOT, "example", "example_axi.json")
    cfg = json_parser(cfg_path)
    settings = Settings(cfg_path, cfg["settings"])
    bus = Bus(cfg["bus"])
    module = Module(cfg["module"], bus, settings)
    gen_settings = {
        "dir": str(out_dir),
        "force_ow": True,
        "force_ow_top": True,
        "update_top": False,
        "gen_bus": False,
        "gen_doc": False,
        "gen_pdf": False,
        "gen_tb": False,
        "gen_header": False,
        "gen_mod": False,
        "gen_localbus": gen_localbus,
    }
    generate_output(settings, bus, module, None, None, None, gen_settings)
    return os.path.join(str(out_dir), "example_axi", "hdl")


_LOCALBUS_FILES = (
    "example_axi_regfile_pkg.vhd",
    "example_axi_regfile.vhd",
    "example_axi_axi_endpoint.vhd",
    "example_axi.vhd",
)


def test_localbus_flag_emits_local_bus_files(tmp_path):
    hdl = _generate_only_localbus(tmp_path, gen_localbus=True)
    for name in _LOCALBUS_FILES:
        assert os.path.isfile(os.path.join(hdl, name))


def test_localbus_flag_off_emits_nothing(tmp_path):
    hdl = _generate_only_localbus(tmp_path, gen_localbus=False)
    for name in _LOCALBUS_FILES:
        assert not os.path.isfile(os.path.join(hdl, name))


def test_empty_module_is_mapped_returns_false():
    """is_mapped must be valid VHDL when the module has no registers."""
    module = Module({"name": "empty", "register": []}, _axi_bus(), settings=None)
    out = GeneratorFactory.generate_regfile_package_vhdl(module)
    assert "return false;" in out
    assert "return ;" not in out
