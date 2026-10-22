"""bust 1.0 reads the register maps written for bust 0.14."""

import json
import logging
import os

import pytest

from bust.core.bus import Bus
from bust.core.enums import FieldType, RegisterType
from bust.core.module import Module

_DATA = os.path.join(os.path.dirname(__file__), "data", "bust_0_14")


def _load(name):
    with open(os.path.join(_DATA, f"{name}.json")) as fp:
        data = json.load(fp)
    # bust 1.0 rejects pulse_cycles other than 1 and any stall_cycles, because it
    # cannot honour them (docs/register-map-format.md). Everything else in the
    # file is read as it is.
    for reg in data["module"]["register"]:
        reg.pop("pulse_cycles", None)
        reg.pop("stall_cycles", None)
    return data


@pytest.mark.parametrize("name", ["example_axi", "example_ipbus"])
def test_bust_0_14_example_parses(name, caplog):
    data = _load(name)
    with caplog.at_level(logging.WARNING):
        module = Module(data["module"], Bus(data["bus"]), settings=None)
    assert len(module.registers) == 12
    assert "'sl' and 'slv' are deprecated" in caplog.text
    assert "(17 registers and fields)" in caplog.text


def test_sl_and_slv_become_bit_and_vector():
    data = _load("example_axi")
    module = Module(data["module"], Bus(data["bus"]), settings=None)
    types = {reg.name: reg.type for reg in module.registers}
    assert types["reg0"] is RegisterType.BIT
    assert types["reg3"] is RegisterType.VECTOR
    assert {f.type for f in module.registers[7].fields} == {
        FieldType.BIT,
        FieldType.VECTOR,
    }


def test_current_type_names_do_not_warn(caplog):
    data = _load("example_axi")
    for reg in data["module"]["register"]:
        reg["type"] = {"sl": "bit", "slv": "vector"}.get(reg["type"], reg["type"])
        for field in reg.get("fields", []):
            field["type"] = {"sl": "bit", "slv": "vector"}[field["type"]]
    with caplog.at_level(logging.WARNING):
        Module(data["module"], Bus(data["bus"]), settings=None)
    assert "deprecated" not in caplog.text
