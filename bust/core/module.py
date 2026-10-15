"""Module management for bus slave generation.

This module defines the Module class which represents a complete bus slave
module with all its registers, configuration settings, and the capability
to generate VHDL code. It handles register address assignment, validation,
and coordination with bus interface code generation.
"""

import logging
import json
from collections import OrderedDict
from typing import TYPE_CHECKING, Dict, List, cast

from bust.core.enums import RegisterMode
from bust.exceptions import (
    FormatError,
    InvalidAddress,
    InvalidRegister,
    InvalidRegisterFormat,
)
from bust.core.register import Register
from bust.utils.formatting import indent_string
from bust.validation.vhdl_validator import is_unique, is_valid_VHDL
from bust.validation.config_validator import ConfigWrapper

if TYPE_CHECKING:
    from bust.core.bus import Bus
    from bust.core.field import Field
    from bust.settings import Settings


class Module:
    """Represents a complete bus slave module with registers.

    The Module class is the top-level container for a bus slave module
    definition. It manages registers, address assignment, and coordinates
    with the Bus and Settings to generate complete VHDL code including
    package files, module entities, and protocol interfaces.

    Attributes:
        name: Module name (must be valid VHDL identifier).
        description: Optional module description.
        version: Module version string.
        git_hash: Git commit hash (currently unused).
        byte_addressable: Whether addresses are byte-based (defaults to the bus).
        addr_width: Address bus width in bits.
        data_width: Data bus width in bits.
        bus: Bus configuration instance.
        settings: Project settings instance.
        registers: List of Register objects in this module.
        addresses: List of assigned register addresses.
    """

    def __init__(self, mod: Dict, bus: "Bus", settings: "Settings") -> None:
        """Initialize a Module instance.

        Args:
            mod: Dictionary containing module configuration with keys:
                - name: Module identifier (required)
                - description: Module description (default: "")
                - version: Version string (default: "")
                - git_hash: Git hash for tracking (optional)
                - byte_addressable: Use byte addressing (default: from the bus)
                - register: List of register configurations (required)
            bus: Bus interface configuration.
            settings: Project-wide settings.

        Raises:
            InvalidAddress: If register addresses conflict.
            InvalidRegister: If register configuration is invalid.
            ValueError: If module name is not a valid VHDL identifier.
        """

        self.logger = logging.getLogger(__name__)

        self.bus = bus
        self.settings = settings
        self.registers: List[Register] = []
        self.addresses: List[int] = []

        self._config = ConfigWrapper(
            mod,
            required_keys=[
                "name",
            ],
            defaults={
                "description": "",
                "version": "",
                "git_hash": None,
                "byte_addressable": bus.byte_addressable,
            },
        )

        self.name = self._config.require("name")
        is_valid_VHDL(self.name)

        # Store some config values for easy access
        self.description: str = self._config.get("description")
        self.version = self._config.get("version")
        self.git_hash = self._config.get("git_hash")  # Currently not used
        self.byte_addressable = self._config.get("byte_addressable")

        self.addr_width = bus.addr_width
        self.data_width = bus.data_width

        for reg in mod["register"]:
            self.add_register(reg)

    def add_register(self, reg: Dict) -> None:
        """Add a register to the module.

        If no address is specified, automatically assigns the next available
        address based on byte_addressable setting. Validates address conflicts.

        Args:
            reg: Dictionary containing register configuration (see Register.__init__).

        Raises:
            FormatError: If the specified address is malformed, out of range or
                unaligned.
            InvalidAddress: If specified address is already in use.
            InvalidRegister: If register configuration is invalid.
            RuntimeError: If address space is exhausted.
        """
        if "address" in reg:
            addr = self._explicit_address(reg)
            if not self.is_address_free(addr):
                raise InvalidAddress(reg.get("name", "<unknown>"), addr)
            self.addresses.append(addr)
        else:
            addr = self.get_next_address()
        try:
            register = Register(reg, addr, self.name, self.data_width)
            self._check_register_name(register.name)
        except Exception as e:
            self.logger.debug(f"Register configuration: {reg}")
            raise InvalidRegister(reg, e) from e
        self.registers.append(register)

    def _explicit_address(self, reg: Dict) -> int:
        """Parse a register's `address` and check that the bus can reach it."""
        name = reg.get("name", "<unknown>")
        address = reg["address"]
        try:
            addr = int(address, 16)
        except (TypeError, ValueError):
            raise FormatError(
                f"Address of register {name} must be a hex string such as "
                f'"0x10" (got {address!r})'
            ) from None
        if self.is_address_out_of_range(addr):
            raise FormatError(
                f"Address {hex(addr)} of register {name} does not fit in "
                f"addr_width {self.addr_width}"
            )
        stride = self.data_width // 8 if self.byte_addressable else 1
        if addr % stride:
            raise FormatError(
                f"Address {hex(addr)} of register {name} is not a multiple of "
                f"{stride}, the data width in bytes"
            )
        return addr

    def _check_register_name(self, name: str) -> None:
        """Reject names that would generate clashing VHDL declarations."""
        if name.lower() == self.name.lower():
            raise InvalidRegisterFormat(
                f"Register {name} has the name of its module, so their VHDL "
                "types would clash"
            )
        is_unique(name, [reg.name for reg in self.registers])

    def get_next_address(self) -> int:
        """Find next available register address.

        Scans for the next free address considering byte_addressable setting.
        For byte-addressable modules (e.g., AXI), increments by data_width/8.
        For word-addressable modules (e.g., IPBus), increments by 1.

        Returns:
            Next available address.

        Raises:
            RuntimeError: If no free address is found within address space.
        """
        addr = 0
        found_addr = False
        while not found_addr:
            if self.is_address_out_of_range(addr):
                raise RuntimeError(
                    "Address " + hex(addr) + " is definitely out of range..."
                )
            if self.is_address_free(addr):
                self.addresses.append(addr)
                return addr
            else:
                if self.byte_addressable:
                    addr += (
                        self.data_width // 8
                    )  # force integer division to prevent float
                else:
                    addr += 1
        return addr

    def is_address_out_of_range(self, addr: int) -> bool:
        """Check if address exceeds address space.

        Args:
            addr: Address to check.

        Returns:
            True if address exceeds 2^addr_width - 1, False otherwise.
        """

        if addr > pow(2, self.addr_width) - 1:
            return True

        return False

    def is_address_free(self, addr: int) -> bool:
        """Check if address is available for assignment.

        Args:
            addr: Address to check.

        Returns:
            True if address is not used by any register, False if occupied.
        """
        for address in self.addresses:
            if address == addr:
                return False
        # If loop completes without matching addresses
        return True

    def is_address_byte_based(self, addr: int) -> bool:
        """Check if address aligns to byte boundaries.

        Args:
            addr: Address to check.

        Returns:
            True if address is divisible by data_width/8 bytes.
        """

        if addr % (self.data_width // 8) == 0:
            return True
        else:
            return False

    def update_addresses(self) -> None:
        """Reassign addresses to all registers sequentially.

        Clears current addresses and assigns new sequential addresses
        using get_next_address() logic.
        """
        self.addresses = []
        for reg in self.registers:
            addr = self.get_next_address()
            reg.address = addr

    @property
    def stored_registers(self) -> List[Register]:
        """Registers with at least one state-holding field."""
        return [reg for reg in self.registers if reg.stored_fields]

    @property
    def to_hw_registers(self) -> List[Register]:
        """Registers with at least one hardware-readable field."""
        return [reg for reg in self.registers if reg.in_to_hw]

    @property
    def from_hw_registers(self) -> List[Register]:
        """Registers with at least one hardware-driven field."""
        return [reg for reg in self.registers if reg.in_from_hw]

    @property
    def strobe_registers(self) -> List[Register]:
        """Registers with a swmod/swacc/singlepulse to_hw strobe output."""
        return [reg for reg in self.registers if reg.has_strobes]

    @property
    def enum_fields(self) -> List["Field"]:
        """Every enumerated field across the module, in register order."""
        return [field for reg in self.registers for field in reg.enum_fields]

    @property
    def register_select_width(self) -> int:
        """Bits needed to decode this module's register window (C_MODULE_ADDR_WIDTH).

        Covers the span from offset 0 to the last register plus one stride, so the
        window is a power-of-two byte range the base address must align to.
        """
        stride = self.data_width // 8 if self.byte_addressable else 1
        top = max((reg.address for reg in self.registers), default=0) + stride
        return max(1, (top - 1).bit_length())

    @property
    def num_ro_regs(self) -> int:
        """Count of read-only registers.

        Returns:
            Number of registers with RO mode.
        """
        return sum(1 for reg in self.registers if reg.mode == RegisterMode.RO)

    @property
    def num_rw_regs(self) -> int:
        """Count of read-write registers.

        Returns:
            Number of registers with RW mode.
        """
        return sum(1 for reg in self.registers if reg.mode == RegisterMode.RW)

    @property
    def num_pulse_regs(self) -> int:
        """Count of pulse registers.

        Returns:
            Number of registers with PULSE mode.
        """
        return sum(1 for reg in self.registers if reg.mode == RegisterMode.PULSE)

    def __str__(self) -> str:
        string = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + self.description + "\n\n"
        string += "Registers: \n"
        for reg in self.registers:
            string += indent_string(str(reg), 1)
        return cast(str, string)

    def to_json(self, include_address: bool = False) -> str:
        """Export complete module configuration as JSON string.

        Every register is written in the schema it was authored in (see
        Register.to_json), so parsing the output rebuilds an identical module.

        Args:
            include_address: Whether to include explicit address values in output
                (default: False).

        Returns:
            JSON string with settings, bus, and module configuration.
        """
        dic = OrderedDict()
        mod = OrderedDict()
        dic["settings"] = self.settings.to_json()
        dic["bus"] = self.bus.to_json()
        dic["module"] = OrderedDict()

        mod["name"] = self.name
        if self.version is not None:
            mod["version"] = self.version
        mod["description"] = self.description
        if self.git_hash is not None:
            mod["git_hash"] = self.git_hash
        if self._config.is_set("byte_addressable"):
            mod["byte_addressable"] = self.byte_addressable

        mod["register"] = [reg.to_json(include_address) for reg in self.registers]

        dic["module"] = mod

        s = json.dumps(dic, indent=4)
        s += "\n"

        return s
