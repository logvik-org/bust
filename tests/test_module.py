"""Unit tests for Module address assignment, range checks, and register
bookkeeping. Uses a lightweight stub bus so the domain logic is exercised
without the generator/template stack."""

from types import SimpleNamespace

import pytest

from bust.core.module import Module
from bust.core.enums import RegisterMode
from bust.exceptions import InvalidAddress, InvalidRegister, InvalidRegisterFormat
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
        with pytest.raises(RuntimeError):
            make_module(
                [{"name": "R0", "mode": "rw", "address": "0x100"}],
                bus=stub_bus(addr_width=4),
            )

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
