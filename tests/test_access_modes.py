"""Unit tests for the bust 1.0 access-mode model: enums, field-level access modes,
register-level inheritance, legacy-schema translation, and validation."""

import pytest

from bust.core.enums import SwAccess, HwAccess, OnRead, OnWrite
from bust.core.field import Field
from bust.core.register import Register
from bust.core.legacy_schema import register_access_defaults, uses_new_schema
from bust.exceptions import InvalidFieldFormat, InvalidRegisterFormat


class TestAccessEnums:
    def test_sw_values(self):
        assert SwAccess.valid_values() == ["rw", "ro", "wo", "na"]

    def test_hw_values(self):
        assert HwAccess.valid_values() == ["r", "w", "rw", "na"]

    def test_onread_values(self):
        assert OnRead.valid_values() == ["rclr", "rset"]

    def test_onwrite_values(self):
        assert OnWrite.valid_values() == [
            "woset",
            "woclr",
            "wot",
            "wzs",
            "wzc",
            "wzt",
            "wclr",
            "wset",
        ]

    def test_from_string_case_insensitive(self):
        assert SwAccess.from_string("RW") is SwAccess.RW
        assert HwAccess.from_string("Rw") is HwAccess.RW
        assert OnWrite.from_string("WOCLR") is OnWrite.WOCLR

    def test_from_string_rejects_unknown(self):
        with pytest.raises(ValueError):
            SwAccess.from_string("readwrite")
        with pytest.raises(ValueError):
            OnRead.from_string("clr")


def make_field(cfg, inherited=None, pos_low=0):
    base = {"name": "f", "type": "bit"}
    base.update(cfg)
    return Field(base, pos_low, "reg", inherited=inherited)


class TestFieldAccessModes:
    def test_defaults_when_unset(self):
        f = make_field({})
        assert f.sw is SwAccess.RW
        assert f.hw is HwAccess.R
        assert f.onread is None and f.onwrite is None
        assert not any([f.we, f.wel, f.hwset, f.hwclr, f.swmod, f.swacc, f.singlepulse])

    def test_field_override(self):
        f = make_field({"sw": "ro", "hw": "w", "we": True})
        assert f.sw is SwAccess.RO
        assert f.hw is HwAccess.W
        assert f.we is True

    def test_inherits_register_default(self):
        f = make_field({}, inherited={"sw": "wo", "hw": "na"})
        assert f.sw is SwAccess.WO
        assert f.hw is HwAccess.NA

    def test_field_overrides_inherited(self):
        f = make_field({"sw": "rw"}, inherited={"sw": "wo"})
        assert f.sw is SwAccess.RW

    def test_onread_onwrite(self):
        f = make_field({"onread": "rclr", "onwrite": "woset"})
        assert f.onread is OnRead.RCLR
        assert f.onwrite is OnWrite.WOSET

    def test_read_only_constant_holds_no_state(self):
        assert not make_field({"sw": "ro", "hw": "r"}).holds_state
        assert not make_field({"sw": "ro", "hw": "na"}).holds_state

    def test_modifiable_fields_hold_state(self):
        assert make_field({"sw": "rw", "hw": "r"}).holds_state
        assert make_field({"sw": "wo", "hw": "r"}).holds_state
        assert make_field({"sw": "ro", "hw": "w"}).holds_state
        assert make_field({"sw": "ro", "hw": "r", "hwset": True}).holds_state
        assert make_field({"sw": "ro", "hw": "r", "hwclr": True}).holds_state
        assert make_field({"sw": "rw", "hw": "r", "onread": "rclr"}).holds_state


class TestFieldEnums:
    def test_parse_enums(self):
        f = Field(
            {
                "name": "mode",
                "type": "vector",
                "width": 2,
                "enums": [
                    {"name": "IDLE", "value": 0},
                    {"name": "BURST", "value": 3},
                ],
            },
            0,
            "reg",
        )
        assert [e.name for e in f.enums] == ["IDLE", "BURST"]
        assert [e.value for e in f.enums] == [0, 3]

    def test_enum_value_out_of_range(self):
        with pytest.raises(InvalidFieldFormat):
            Field(
                {
                    "name": "mode",
                    "type": "vector",
                    "width": 2,
                    "enums": [{"name": "TOOBIG", "value": 4}],
                },
                0,
                "reg",
            )

    def test_duplicate_enum_value(self):
        with pytest.raises(InvalidFieldFormat):
            Field(
                {
                    "name": "mode",
                    "type": "vector",
                    "width": 2,
                    "enums": [
                        {"name": "A", "value": 1},
                        {"name": "B", "value": 1},
                    ],
                },
                0,
                "reg",
            )

    def test_duplicate_enum_name(self):
        with pytest.raises(InvalidFieldFormat):
            Field(
                {
                    "name": "mode",
                    "type": "vector",
                    "width": 2,
                    "enums": [
                        {"name": "A", "value": 0},
                        {"name": "A", "value": 1},
                    ],
                },
                0,
                "reg",
            )

    def test_invalid_vhdl_enum_name(self):
        with pytest.raises(Exception):
            Field(
                {
                    "name": "mode",
                    "type": "vector",
                    "width": 2,
                    "enums": [{"name": "1bad", "value": 0}],
                },
                0,
                "reg",
            )

    def test_explicit_reset_outside_enum_set_rejected(self):
        with pytest.raises(InvalidFieldFormat):
            Field(
                {
                    "name": "mode",
                    "type": "vector",
                    "width": 2,
                    "reset": "0x2",
                    "enums": [
                        {"name": "A", "value": 0},
                        {"name": "B", "value": 1},
                        {"name": "D", "value": 3},
                    ],
                },
                0,
                "reg",
            )

    def test_explicit_reset_matching_enum_value_accepted(self):
        f = Field(
            {
                "name": "mode",
                "type": "vector",
                "width": 2,
                "reset": "0x3",
                "enums": [{"name": "A", "value": 0}, {"name": "D", "value": 3}],
            },
            0,
            "reg",
        )
        assert f.reset_value_vhdl == "D"


class TestSchemaConflicts:
    def test_legacy_mode_mixed_with_new_keys_rejected(self):
        with pytest.raises(InvalidRegisterFormat):
            Register(
                {
                    "name": "reg",
                    "mode": "pulse",
                    "sw": "rw",
                    "hw": "r",
                    "type": "fields",
                    "fields": [{"name": "f0", "type": "bit"}],
                },
                0,
                "m",
                32,
            )

    def test_legacy_mode_alone_accepted(self):
        reg = Register({"name": "reg", "mode": "ro", "type": "default"}, 0, "m", 32)
        assert reg.sw is SwAccess.RO


class TestLegacyTranslation:
    def test_rw_maps_to_sw_rw_hw_r(self):
        assert register_access_defaults({"mode": "rw"}) == {"sw": "rw", "hw": "r"}

    def test_ro_maps_to_sw_ro_hw_w(self):
        assert register_access_defaults({"mode": "ro"}) == {"sw": "ro", "hw": "w"}

    def test_pulse_maps_to_singlepulse(self):
        d = register_access_defaults({"name": "p", "mode": "pulse"})
        assert d == {"sw": "wo", "hw": "r", "singlepulse": True}

    def test_pulse_cycles_warns(self, caplog):
        register_access_defaults({"name": "p", "mode": "pulse", "pulse_cycles": 4})
        assert "single-cycle" in caplog.text

    def test_absent_mode_defaults_rw(self):
        assert register_access_defaults({"name": "r"}) == {"sw": "rw", "hw": "r"}

    def test_new_schema_detected(self):
        assert uses_new_schema({"sw": "ro"})
        assert not uses_new_schema({"mode": "rw"})

    def test_new_schema_passed_through(self):
        d = register_access_defaults({"sw": "wo", "hw": "na", "onwrite": "woclr"})
        assert d == {"sw": "wo", "hw": "na", "onwrite": "woclr"}


class TestRegisterInheritance:
    def _fields_reg(self, extra):
        cfg = {
            "name": "r",
            "type": "fields",
            "fields": [
                {"name": "f0", "type": "bit"},
                {"name": "f1", "type": "bit", "sw": "rw"},
            ],
        }
        cfg.update(extra)
        return Register(cfg, 0, "mod", 32)

    def test_legacy_ro_register_fields_inherit(self):
        reg = self._fields_reg({"mode": "ro"})
        assert reg.sw is SwAccess.RO and reg.hw is HwAccess.W
        assert reg.fields[0].sw is SwAccess.RO
        assert reg.fields[0].hw is HwAccess.W
        # field override still wins
        assert reg.fields[1].sw is SwAccess.RW

    def test_legacy_pulse_register_fields_inherit_singlepulse(self):
        reg = self._fields_reg({"mode": "pulse"})
        assert reg.fields[0].singlepulse is True
        assert reg.fields[0].sw is SwAccess.WO

    def test_new_schema_register_fields_inherit(self):
        reg = self._fields_reg({"sw": "ro", "hw": "w"})
        assert reg.fields[0].sw is SwAccess.RO
        assert reg.fields[0].hw is HwAccess.W
        assert reg.fields[1].sw is SwAccess.RW

    def test_register_modifier_inherited_by_fields(self):
        reg = self._fields_reg({"hw": "w", "we": True})
        assert reg.fields[0].we is True
        assert reg.fields[0].hw is HwAccess.W


class TestAccessModeValidation:
    def _f(self, cfg):
        base = {"name": "f", "type": "bit"}
        base.update(cfg)
        return Field(base, 0, "reg")

    def test_no_access_rejected(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "na", "hw": "na"})

    def test_we_and_wel_conflict(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"hw": "w", "we": True, "wel": True})

    def test_we_requires_hw_writable(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"hw": "r", "we": True})

    def test_onread_requires_sw_readable(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "wo", "onread": "rclr"})

    def test_onwrite_requires_sw_writable(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "ro", "onwrite": "woset"})

    def test_onwrite_and_singlepulse_conflict(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "rw", "onwrite": "woset", "singlepulse": True})

    def test_singlepulse_requires_sw_writable(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "ro", "singlepulse": True})

    def test_swmod_requires_sw_writable(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "ro", "swmod": True})

    def test_swacc_requires_sw_access(self):
        with pytest.raises(InvalidFieldFormat):
            self._f({"sw": "na", "hw": "w", "swacc": True})

    def test_valid_combinations_accepted(self):
        # mirror prototype fields that must remain legal
        self._f({"sw": "rw", "hw": "rw", "we": True})  # reg4.field0
        self._f({"sw": "rw", "hw": "r", "hwset": True, "hwclr": True})  # reg4.field1
        self._f({"sw": "rw", "hw": "r", "onread": "rclr"})  # reg5.field0
        self._f({"sw": "rw", "hw": "r", "onwrite": "woset"})  # reg6.field0
        self._f({"sw": "rw", "hw": "r", "swmod": True})  # reg9.field0
        self._f({"sw": "rw", "hw": "r", "singlepulse": True})  # reg10.field0
        self._f({"sw": "ro", "hw": "w", "wel": True})  # reg1.field2
