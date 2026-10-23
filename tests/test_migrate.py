"""bust FILE --migrate, on a module written by bust 0.14.1 with user logic added."""

import json
import logging
import os
import shutil

import pytest

from bust.editing.document import EditRejected, RegisterMapDocument
from bust.migrate import conversion, migrate, migrate_register_map

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_DATA = os.path.join(_REPO_ROOT, "tests", "data", "migrate")


def test_register_map():
    cfg = {
        "settings": {"mod_subdir": True, "coverage": True},
        "bus": {"type": "axi", "addr_width": 32, "data_width": 32, "reset": "x"},
        "module": {
            "name": "m",
            "byte_addressable": "False",
            "register": [
                {"name": "a", "mode": "pulse", "type": "sl", "pulse_cycles": 1},
                {
                    "name": "b",
                    "address": "10",
                    "reset": "9",
                    "type": "fields",
                    "fields": [{"name": "f", "type": "slv", "reset": "0b1"}],
                },
            ],
        },
    }

    migrate_register_map(cfg)

    assert "settings" not in cfg
    assert "reset" not in cfg["bus"]
    assert cfg["module"]["byte_addressable"] is False
    a, b = cfg["module"]["register"]
    assert a == {"name": "a", "mode": "pulse", "type": "bit"}
    assert (b["address"], b["reset"]) == ("0x10", "9")
    assert b["fields"][0] == {"name": "f", "type": "vector", "reset": "0x0b1"}


@pytest.mark.parametrize("kind", ["ipbus", "axi"])
def test_top_level(tmp_path, kind):
    shutil.copytree(os.path.join(_DATA, kind), str(tmp_path / kind))
    json_file = tmp_path / kind / "blinky.json"
    top = tmp_path / kind / "blinky" / "hdl" / "blinky.vhd"
    old = top.read_text()

    migrate(str(json_file), None, force=True)

    new = top.read_text()
    prefix = "ipb" if kind == "ipbus" else "axi"
    entity = old[old.index("entity blinky is") : old.index("end entity blinky;")]
    assert entity in new
    assert "counter <= counter + unsigned(to_hw.ctrl.rate);" in new
    assert "from_hw.count <= std_logic_vector(counter);" in new
    assert f": entity work.blinky_{prefix}_endpoint" in new
    assert "t_blinky_from_hw := C_BLINKY_FROM_HW_RESET;" in new
    assert ('G_UNMAPPED_READ_DATA => x"DEADBEEF"' in new) == (kind == "ipbus")
    assert ("G_ERR_ON_BAD_ACCESS  => true" in new) == (kind == "ipbus")
    assert "_pif" not in new and f"{prefix}_rw_regs" not in new
    assert (tmp_path / kind / "blinky" / "hdl" / "blinky.vhd.0_14").read_text() == old
    registers = json.loads(json_file.read_text())["module"]["register"]
    assert registers[2]["address"] == "0x10"
    assert list(registers[2])[:4] == ["name", "sw", "hw", "singlepulse"]
    assert [r["sw"] for r in registers] == ["rw", "ro", "wo"]


def test_output_without_module_directory(tmp_path, caplog):
    """A 0.14 file with "mod_subdir": false kept its output beside the JSON file."""
    shutil.copytree(os.path.join(_DATA, "ipbus", "blinky"), str(tmp_path / "blinky"))
    json_file = tmp_path / "blinky" / "blinky.json"
    cfg = json.loads(open(os.path.join(_DATA, "ipbus", "blinky.json")).read())
    cfg["settings"] = {"mod_subdir": False}
    json_file.write_text(json.dumps(cfg))

    with caplog.at_level(logging.INFO):
        migrate(str(json_file), None, force=True)

    assert "to_hw" in (tmp_path / "blinky" / "hdl" / "blinky.vhd").read_text()
    assert f"Now run bust {json_file} -o {tmp_path}." in caplog.text


_JSON5 = """{
  // A bust 0.14 register map
  bus: {type: "axi", addr_width: 32, data_width: 32},
  module: {
    name: "m",
    register: [
      {name: "ctrl", mode: "rw", type: "sl", address: 0x0}, // control
    ],
  },
}
"""


def test_json5_keeps_its_text_except_the_changes(tmp_path):
    json_file = tmp_path / "m.json5"
    json_file.write_text(_JSON5)

    migrate(str(json_file), None, force=True)

    assert json_file.read_text() == _JSON5.replace(
        'mode: "rw", type: "sl"', 'sw: "rw", hw: "r", type: "bit"'
    )
    assert (tmp_path / "m.json5.0_14").read_text() == _JSON5


def test_nothing_to_migrate(tmp_path, caplog):
    json_file = tmp_path / "m.json5"
    text = _JSON5.replace('mode: "rw", type: "sl"', 'sw: "rw", hw: "r", type: "bit"')
    json_file.write_text(text)

    with caplog.at_level(logging.INFO):
        migrate(str(json_file), None, force=True)

    assert "Nothing to migrate." in caplog.text
    assert json_file.read_text() == text
    assert not (tmp_path / "m.json5.0_14").exists()


def test_conversion_gives_back_the_example(tmp_path):
    """The example, with each register's access keys turned back into the
    bust 0.14 mode, converts to the example as it is shipped."""
    with open(os.path.join(_REPO_ROOT, "example", "example_axi.json")) as fp:
        example = fp.read()
    indent = "\n" + " " * 16
    old = example
    for mode, keys in [
        ("pulse", ['"sw": "wo"', '"hw": "r"', '"singlepulse": true']),
        ("ro", ['"sw": "ro"', '"hw": "w"']),
        ("rw", ['"sw": "rw"', '"hw": "r"']),
    ]:
        old = old.replace(
            indent + ("," + indent).join(keys) + ",", indent + f'"mode": "{mode}",'
        )
    assert old.count('"mode"') == 12
    json_file = tmp_path / "example_axi.json"
    json_file.write_text(old)
    document = RegisterMapDocument.open(str(json_file))

    _, operations = conversion(document)
    document.apply(operations)

    assert document.text == example
    assert conversion(document) == ([], [])


def test_conversion_of_a_file_bust_1_0_rejects(tmp_path):
    # Its address "10" is hexadecimal in bust 0.14 and not a multiple of 4 in 1.0.
    json_file = tmp_path / "blinky.json"
    shutil.copyfile(os.path.join(_DATA, "axi", "blinky.json"), str(json_file))
    document = RegisterMapDocument.open(str(json_file))
    with pytest.raises(EditRejected, match="Run bust with --migrate"):
        document.check()

    changes, operations = conversion(document)
    document.apply(operations)

    assert changes[:3] == [
        "removed the settings section",
        "removed bus.comp_library",
        "enable: type is now bit",
    ]
    assert 'clear: address "10" is now "0x10"' in changes
    assert 'ctrl: mode rw is now sw "rw", hw "r"' in changes
    assert [reg.address for reg in document.module.registers] == [0x0, 0x4, 0x10]


@pytest.mark.parametrize(
    "keys, message",
    [
        ('mode: "pulse", pulse_cycles: 2', "pulse_cycles=2 is not supported"),
        ('mode: "rw", stall_cycles: 30', "stall_cycles is not supported"),
        ('mode: "pulse", pulse_cycles: "two"', "pulse_cycles of register ctrl"),
        ('mode: "ro", sw: "rw"', "'mode' key together with access keys"),
    ],
)
def test_conversion_rejects_what_bust_1_0_cannot_generate(tmp_path, keys, message):
    json_file = tmp_path / "m.json5"
    json_file.write_text(_JSON5.replace('mode: "rw"', keys))
    document = RegisterMapDocument.open(str(json_file))

    with pytest.raises(EditRejected, match=message):
        conversion(document)


def test_timing_bust_1_0_has_is_removed(tmp_path):
    json_file = tmp_path / "m.json5"
    json_file.write_text(
        _JSON5.replace('mode: "rw"', 'mode: "pulse", pulse_cycles: 1, stall_cycles: 0')
    )

    migrate(str(json_file), None, force=True)

    assert json_file.read_text() == _JSON5.replace(
        'mode: "rw", type: "sl"', 'sw: "wo", hw: "r", singlepulse: true, type: "bit"'
    )
