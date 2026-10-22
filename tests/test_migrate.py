"""bust FILE --migrate, on a module written by bust 0.14.1 with user logic added."""

import json
import logging
import os
import shutil

import pytest

from bust.migrate import migrate, migrate_register_map

_DATA = os.path.join(os.path.dirname(__file__), "data", "migrate")


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
