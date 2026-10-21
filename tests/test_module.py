"""Unit tests for Module address assignment, range checks, and register
bookkeeping. Uses a lightweight stub bus so the domain logic is exercised
without the generator/template stack."""

import json
from types import SimpleNamespace

import pytest

from bust.core.module import Module
from bust.core.enums import RegisterMode
from bust.exceptions import (
    FormatError,
    InvalidAddress,
    InvalidRegister,
    InvalidRegisterFormat,
)
from bust.validation.vhdl_validator import InvalidVHDLIdentifier


def stub_bus(bus_type="axi", addr_width=8, data_width=32):
    return SimpleNamespace(
        bus_type=bus_type,
        addr_width=addr_width,
        data_width=data_width,
        byte_addressable=(bus_type == "axi"),
    )


def make_module(registers, bus=None):
    bus = bus or stub_bus()
    return Module({"name": "testmod", "register": registers}, bus, settings=None)


def regs(*names):
    return [{"name": name, "mode": "rw"} for name in names]


class TestAddressAssignment:
    def test_byte_addressable_steps_by_word(self):
        mod = make_module(regs("R0", "R1", "R2"))
        assert mod.addresses == [0, 4, 8]

    def test_word_addressable_steps_by_one(self):
        mod = make_module(regs("R0", "R1", "R2"), bus=stub_bus(bus_type="ipbus"))
        assert mod.addresses == [0, 1, 2]

    def test_word_addressing_on_a_byte_bus(self):
        # bust 0.14 allowed this on AXI, and the endpoint compares the address
        # as the master drives it.
        mod = Module(
            {
                "name": "testmod",
                "byte_addressable": False,
                "register": regs("R0", "R1") + [{"name": "R2", "address": "0x3"}],
            },
            stub_bus(),
            settings=None,
        )
        assert mod.addresses == [0, 1, 3]

    @pytest.mark.parametrize("value, step", [("True", 4), ("False", 1)])
    def test_byte_addressable_reads_the_0_14_strings(self, value, step, caplog):
        bus = stub_bus()
        bus.to_json = dict
        mod = Module(
            {
                "name": "testmod",
                "byte_addressable": value,
                "register": regs("R0", "R1"),
            },
            bus,
            settings=SimpleNamespace(to_json=dict),
        )
        assert mod.addresses == [0, step]
        assert f'byte_addressable "{value}" is the deprecated bust 0.14 form' in (
            caplog.text
        )
        # Saving writes the JSON boolean.
        saved = json.loads(mod.to_json())["module"]["byte_addressable"]
        assert saved is (value == "True")

    @pytest.mark.parametrize("value", ["false", "yes", 0])
    def test_byte_addressable_must_be_a_boolean(self, value):
        with pytest.raises(FormatError, match="byte_addressable must be true or false"):
            Module(
                {"name": "testmod", "byte_addressable": value, "register": regs("R0")},
                stub_bus(),
                settings=None,
            )

    def test_explicit_address_honoured(self):
        mod = make_module([{"name": "R0", "mode": "rw", "address": "0x10"}])
        assert mod.registers[0].address == 0x10

    def test_conflicting_explicit_address_rejected(self):
        with pytest.raises(InvalidAddress):
            make_module(
                [
                    {"name": "R0", "mode": "rw", "address": "0x0"},
                    {"name": "R1", "mode": "rw", "address": "0x0"},
                ]
            )

    def test_out_of_range_address_rejected(self):
        with pytest.raises(FormatError, match="does not fit in addr_width 4"):
            make_module(
                [{"name": "R0", "mode": "rw", "address": "0x100"}],
                bus=stub_bus(addr_width=4),
            )

    def test_unaligned_address_rejected(self):
        with pytest.raises(FormatError, match="not a multiple of 4"):
            make_module([{"name": "R0", "mode": "rw", "address": "0x2"}])

    def test_word_addressed_bus_takes_any_address(self):
        mod = make_module(
            [{"name": "R0", "mode": "rw", "address": "0x3"}],
            bus=stub_bus(bus_type="ipbus"),
        )
        assert mod.addresses == [3]

    def test_numeric_address_is_decimal(self):
        mod = make_module([{"name": "R0", "mode": "rw", "address": 16}])
        assert mod.registers[0].address == 0x10

    def test_update_addresses_reassigns_sequentially(self):
        mod = make_module(regs("R0", "R1"))
        mod.update_addresses()
        assert [reg.address for reg in mod.registers] == [0, 4]


class TestRegisterBookkeeping:
    def test_mode_counts(self):
        mod = make_module(
            [
                {"name": "R0", "mode": "rw"},
                {"name": "R1", "mode": "ro"},
                {"name": "R2", "mode": "pulse"},
                {"name": "R3", "mode": "rw"},
            ]
        )
        assert mod.num_rw_regs == 2
        assert mod.num_ro_regs == 1
        assert mod.num_pulse_regs == 1

    @pytest.mark.parametrize("bus_type", ["axi", "ipbus"])
    def test_stall_rejected_on_every_bus(self, bus_type):
        with pytest.raises(InvalidRegister) as excinfo:
            make_module(
                [{"name": "R0", "mode": "rw", "stall_cycles": 4}],
                bus=stub_bus(bus_type=bus_type),
            )
        assert isinstance(excinfo.value.__cause__, InvalidRegisterFormat)
        assert "stall_cycles is not supported" in str(excinfo.value.__cause__)

    def test_default_byte_addressable_follows_bus_type(self):
        assert make_module(regs("R0")).byte_addressable is True
        assert (
            make_module(regs("R0"), bus=stub_bus(bus_type="ipbus")).byte_addressable
            is False
        )


class TestModuleValidation:
    def test_invalid_name_rejected(self):
        with pytest.raises(InvalidVHDLIdentifier):
            Module({"name": "1bad", "register": []}, stub_bus(), settings=None)

    def test_mode_enum_resolved(self):
        mod = make_module([{"name": "R0", "mode": "pulse"}])
        assert mod.registers[0].mode is RegisterMode.PULSE


def fields_register(name="R0", fields=None, **keys):
    fields = [{"name": "f", "type": "bit"}] if fields is None else fields
    return {"name": name, "sw": "rw", "hw": "r", "fields": fields, **keys}


class TestRegisterMapValidation:
    def test_fields_imply_type_fields(self):
        mod = make_module([fields_register()])
        assert [f.name for f in mod.registers[0].fields] == ["f"]

    def test_fields_on_another_type_rejected(self):
        with pytest.raises(InvalidRegister, match="has fields but type 'vector'"):
            make_module([fields_register(type="vector")])

    def test_empty_fields_rejected(self):
        with pytest.raises(InvalidRegister, match="has no fields"):
            make_module([fields_register(fields=[])])

    def test_register_names_differing_in_case_rejected(self):
        with pytest.raises(InvalidRegister, match="already used"):
            make_module(regs("ctrl", "CTRL"))

    def test_field_names_differing_in_case_rejected(self):
        fields = [{"name": "f", "type": "bit"}, {"name": "F", "type": "bit"}]
        with pytest.raises(InvalidRegister, match="already used"):
            make_module([fields_register(fields=fields)])

    def test_register_named_like_the_module_rejected(self):
        with pytest.raises(InvalidRegister, match="name of its module"):
            make_module(regs("TestMod"))

    def test_quoted_flag_rejected(self):
        fields = [{"name": "f", "type": "bit", "swmod": "false"}]
        with pytest.raises(InvalidRegister, match="must be true or false"):
            make_module([fields_register(fields=fields)])

    def test_null_flag_is_false(self):
        fields = [{"name": "f", "type": "bit", "swmod": None}]
        assert (
            make_module([fields_register(fields=fields)]).registers[0].fields[0].swmod
            is False
        )
