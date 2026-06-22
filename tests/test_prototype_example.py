"""Verify the comprehensive prototype example parses into the v1 access-mode
model: register-level inheritance, field overrides, side effects, modifiers,
and enums. This is the input fixture the regfile generator is developed against."""

from types import SimpleNamespace

import pytest

from bust.core.module import Module
from bust.core.enums import SwAccess, HwAccess, OnRead, OnWrite
from bust.utils.json_utils import json_parser


@pytest.fixture(scope="module")
def prototype():
    config = json_parser("example/example_prototype.json")
    bus = SimpleNamespace(bus_type="axi", addr_width=32, data_width=32)
    return Module(config["module"], bus, settings=None)


def field(mod, reg_name, field_name):
    reg = next(r for r in mod.registers if r.name == reg_name)
    return next(f for f in reg.fields if f.name == field_name)


def test_all_registers_present(prototype):
    assert [r.name for r in prototype.registers] == [f"reg{i}" for i in range(12)]


def test_register_defaults_inherited_by_fields(prototype):
    # reg1 register default is sw ro / hw w; field1 sets nothing of its own.
    f = field(prototype, "reg1", "field1")
    assert f.sw is SwAccess.RO
    assert f.hw is HwAccess.W


def test_field_overrides_register_default(prototype):
    # reg4 default hw r; field0 overrides to hw rw, field1 keeps the default.
    assert field(prototype, "reg4", "field0").hw is HwAccess.RW
    assert field(prototype, "reg4", "field1").hw is HwAccess.R


def test_hw_modifiers(prototype):
    assert field(prototype, "reg1", "field0").we is True
    assert field(prototype, "reg1", "field2").wel is True
    assert field(prototype, "reg4", "field1").hwset is True
    assert field(prototype, "reg4", "field1").hwclr is True
    assert field(prototype, "reg9", "field0").swmod is True
    assert field(prototype, "reg9", "field1").swacc is True
    assert field(prototype, "reg10", "field0").singlepulse is True


def test_software_side_effects(prototype):
    assert field(prototype, "reg5", "field0").onread is OnRead.RCLR
    assert field(prototype, "reg5", "field1").onread is OnRead.RSET
    assert field(prototype, "reg6", "field0").onwrite is OnWrite.WOSET
    assert field(prototype, "reg6", "field1").onwrite is OnWrite.WOCLR
    assert field(prototype, "reg8", "field0").onwrite is OnWrite.WCLR


def test_clear_type_fields_reset_to_ones(prototype):
    # woclr/wzc/wclr fields reset to all 1s so their clearing is observable.
    assert int(field(prototype, "reg6", "field1").reset, 16) == 0xF
    assert int(field(prototype, "reg7", "field1").reset, 16) == 0xF
    assert int(field(prototype, "reg8", "field0").reset, 16) == 0xF


def test_enum_field(prototype):
    enums = field(prototype, "reg11", "field0").enums
    assert [e.name for e in enums] == ["STATE0", "STATE1", "STATE2", "STATE3"]
    assert [e.value for e in enums] == [0, 1, 2, 3]
