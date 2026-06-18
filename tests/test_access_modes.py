"""Unit tests for the v1 access-mode model: enums, field-level access modes,
register-level inheritance, legacy-schema translation, and validation."""

import pytest

from bust.core.enums import SwAccess, HwAccess, OnRead, OnWrite
from bust.core.field import Field
from bust.exceptions import InvalidFieldFormat


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


def make_field(cfg, inherited=None, pos_low=0, width_key=True):
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
