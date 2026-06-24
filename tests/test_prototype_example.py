"""Verify the comprehensive prototype example parses into the bust 1.0 access-mode
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


def reg(mod, name):
    return next(r for r in mod.registers if r.name == name)


def test_to_hw_registers_exclude_write_only_and_na(prototype):
    # reg1 is hw w (not readable), reg3 is hw na; everything else is hw r/rw.
    names = [r.name for r in prototype.to_hw_registers]
    assert "reg1" not in names and "reg3" not in names
    assert {"reg0", "reg4", "reg11"}.issubset(set(names))


def test_from_hw_registers_only_hw_driven(prototype):
    # Only reg1 (hw w) and reg4 (field0 hw rw, field1 hwset/hwclr) are driven.
    assert [r.name for r in prototype.from_hw_registers] == ["reg1", "reg4"]


def test_from_hw_record_shapes(prototype):
    # value+we, plain continuous value, value+wel, set/clr-only.
    assert field(prototype, "reg1", "field0").from_hw_members == ["value", "we"]
    assert field(prototype, "reg1", "field1").from_hw_is_record is False
    assert field(prototype, "reg1", "field2").from_hw_members == ["value", "wel"]
    assert field(prototype, "reg4", "field1").from_hw_members == ["set", "clr"]


def test_to_hw_record_shapes(prototype):
    assert field(prototype, "reg9", "field0").to_hw_members == ["value", "swmod"]
    assert field(prototype, "reg9", "field1").to_hw_members == ["value", "swacc"]
    assert field(prototype, "reg10", "field0").to_hw_is_record is False


def test_enum_field_typing(prototype):
    f = field(prototype, "reg11", "field0")
    assert f.enum_type_name == "t_reg11_field0"
    assert f.value_type_vhdl == "t_reg11_field0"
    assert prototype.enum_fields == [f]


def test_stored_fields_cover_all_demo_fields(prototype):
    # Every field in the demo holds state.
    for register in prototype.registers:
        assert register.stored_fields == register.fields
