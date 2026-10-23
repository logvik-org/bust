"""Module management for bus slave generation.

This module defines the Module class which represents a complete bus slave
module with all its registers, configuration settings, and the capability
to generate VHDL code. It handles register address assignment, validation,
and coordination with bus interface code generation.
"""

import hashlib
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from bust.core.enums import RegisterType
from bust.exceptions import (
    FormatError,
    InvalidAddress,
    InvalidRegister,
    InvalidRegisterFormat,
)
from bust.core.register import Register
from bust.utils.formatting import indent_string
from bust.validation.vhdl_validator import is_unique, is_valid_VHDL
from bust.validation.config_validator import (
    ConfigWrapper,
    parse_number,
)

if TYPE_CHECKING:
    from bust.core.bus import Bus
    from bust.core.field import Field
    from bust.settings import Settings


# The version goes unescaped into VHDL, C, C++ and Python strings and into the
# uHAL parameters of the IPBus address table, which separate entries with ; and
# key from value with =.
VERSION_PATTERN = re.compile(r"[ !#-:<>-\[\]-~]*")

# The version a version register packs into 0x00MMmmpp.
VERSION_NUMBER_PATTERN = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")

MODULE_KEYS = (
    "name",
    "description",
    "version",
    "byte_addressable",
    "register",
)


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
                - byte_addressable: Use byte addressing (default: from the bus)
                - register: List of register configurations (required)
            bus: Bus interface configuration.
            settings: Project-wide settings.

        Raises:
            FormatError: If byte_addressable is not a boolean.
            InvalidAddress: If register addresses conflict.
            InvalidRegister: If register configuration is invalid.
            ValueError: If module name is not a valid VHDL identifier.
        """

        self.logger = logging.getLogger(__name__)

        self.bus = bus
        self.settings = settings
        self.registers: List[Register] = []
        self.addresses: List[int] = []
        # The JSON of the register with type hash, which is rebuilt with the
        # hash as its value once the register map is complete.
        self._hash_register_config: Optional[Dict] = None

        self._config = ConfigWrapper(
            mod,
            required_keys=[
                "name",
            ],
            defaults={
                "description": "",
                "version": "",
                "byte_addressable": bus.byte_addressable,
            },
        )

        self.name = self._config.require("name")
        is_valid_VHDL(self.name)

        # Store some config values for easy access
        self.description: str = self._config.get("description")
        self.version = self._read_version()
        self.byte_addressable = self._read_byte_addressable()

        self.addr_width = bus.addr_width
        self.data_width = bus.data_width

        for reg in mod["register"]:
            self.add_register(reg)
        self._update_hash_register()

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
            if register.type.is_constant:
                self._check_one_constant_register(register)
            if register.type == RegisterType.HASH:
                self._hash_register_config = reg
            elif register.type == RegisterType.VERSION:
                register = Register(
                    reg, addr, self.name, self.data_width, value=self.version_number
                )
        except Exception as e:
            self.logger.debug(f"Register configuration: {reg}")
            raise InvalidRegister(reg, e) from e
        self.registers.append(register)

    def _read_byte_addressable(self) -> bool:
        """Read byte_addressable, which must be true or false."""
        value = self._config.get("byte_addressable")
        if isinstance(value, bool):
            return value
        raise FormatError(f"byte_addressable must be true or false (got {value!r})")

    def _read_version(self) -> str:
        """Read the version, which every generated file carries as a string."""
        value = self._config.get("version")
        if not isinstance(value, str):
            raise FormatError(
                f'version must be a string, such as "1.2" (got {value!r})'
            )
        if not VERSION_PATTERN.fullmatch(value):
            raise FormatError(
                f"version {value!r} may only hold printable ASCII characters "
                'other than ", \\, ; and ='
            )
        return value

    def _explicit_address(self, reg: Dict) -> int:
        """Parse a register's `address` and check that the bus can reach it."""
        name = reg.get("name", "<unknown>")
        addr = parse_number(reg["address"], f"Address of register {name}")
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

    def _check_one_constant_register(self, register: Register) -> None:
        """Reject a second register with type hash, or with type version."""
        kind = register.type.value
        other = self._register_of_type(register.type)
        if other is not None:
            raise InvalidRegisterFormat(
                f"Register {register.name} has type {kind}, and so does "
                f"{other.name}. A module has at most one {kind} register."
            )

    def _register_of_type(self, kind: RegisterType) -> Optional[Register]:
        return next((reg for reg in self.registers if reg.type == kind), None)

    @property
    def hash_register(self) -> Optional[Register]:
        """The register with type hash, or None."""
        return self._register_of_type(RegisterType.HASH)

    @property
    def version_register(self) -> Optional[Register]:
        """The register with type version, or None."""
        return self._register_of_type(RegisterType.VERSION)

    @property
    def version_number(self) -> int:
        """The version as the value of a version register, 0x00MMmmpp.

        Raises:
            FormatError: If the version is not MAJOR.MINOR or
                MAJOR.MINOR.PATCH with each number from 0 to 255.
        """
        match = VERSION_NUMBER_PATTERN.fullmatch(self.version)
        numbers = [int(n or 0) for n in match.groups()] if match else []
        if not numbers or max(numbers) > 255:
            raise FormatError(
                "A version register needs a version of the form MAJOR.MINOR or "
                "MAJOR.MINOR.PATCH, with each number from 0 to 255 "
                f"(version is {self.version!r})"
            )
        major, minor, patch = numbers
        return (major << 16) | (minor << 8) | patch

    def _update_hash_register(self) -> None:
        """Give the hash register the register map hash as its value.

        The hash covers the hash register, apart from its value.
        """
        hash_register = self.hash_register
        if hash_register is None:
            return
        index = self.registers.index(hash_register)
        self.registers[index] = Register(
            cast(Dict, self._hash_register_config),
            hash_register.address,
            self.name,
            self.data_width,
            value=self.regmap_hash,
        )

    @property
    def constant_registers(self) -> List[Register]:
        """The hash and version registers, in register order."""
        return [reg for reg in self.registers if reg.type.is_constant]

    def value_vhdl(self, value: str) -> str:
        """A register value such as "0x1f" as a data-width VHDL literal."""
        digits = (self.data_width + 3) // 4
        return f'{self.data_width}x"{int(value, 16):0{digits}X}"'

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
        self._update_hash_register()

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
        """C_<MODULE>_MODULE_ADDR_WIDTH: the low address bits that select a register.

        Enough bits for every address from 0 to the end of the last register. It
        is the smallest module address width that holds the registers.
        """
        stride = self.data_width // 8 if self.byte_addressable else 1
        top = max((reg.address for reg in self.registers), default=0) + stride
        return max(1, (top - 1).bit_length())

    @property
    def regmap_hash(self) -> int:
        """A 32-bit hash of the register map, which changes when it changes.

        It covers the module name, the data width, the addressing and, for each
        register and field, the name, register offset, position, width, type,
        reset, access modes and enumerations. Descriptions and the version do not
        count, and the hash does not depend on the bus or the bust version. The
        hash is the first 32 bits of the SHA-256 of the canonical JSON of those
        values. The values of the hash and version registers do not count
        either, since they are the hash and the version.
        """
        content: Dict[str, Any] = {
            "hash_format": 1,
            "name": self.name,
            "data_width": self.data_width,
            "byte_addressable": self.byte_addressable,
            "registers": [
                {
                    "name": reg.name,
                    "address": reg.address,
                    "type": reg.type.value,
                    "width": reg.width,
                    "reset": None if reg.type.is_constant else reg.reset,
                    "fields": [
                        _field_content(f, not reg.type.is_constant)
                        for f in reg.effective_fields
                    ],
                }
                for reg in self.registers
            ],
        }
        text = json.dumps(content, sort_keys=True, separators=(",", ":"))
        return int.from_bytes(hashlib.sha256(text.encode()).digest()[:4], "big")

    @property
    def regmap_hash_hex(self) -> str:
        """The register map hash as eight upper-case hexadecimal digits."""
        return f"{self.regmap_hash:08X}"

    def __str__(self) -> str:
        string = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + self.description + "\n\n"
        string += "Registers: \n"
        for reg in self.registers:
            string += indent_string(str(reg), 1)
        return cast(str, string)


def _field_content(field: "Field", with_reset: bool = True) -> Dict[str, Any]:
    """The values of a field that the register map hash covers."""
    return {
        "name": field.name,
        "type": field.type.value,
        "position": field.pos_low,
        "width": field.width,
        "reset": field.reset if with_reset else None,
        "sw": field.sw.value,
        "hw": field.hw.value,
        "onread": field.onread.value if field.onread else None,
        "onwrite": field.onwrite.value if field.onwrite else None,
        "flags": [
            key
            for key in ("singlepulse", "we", "wel", "hwset", "hwclr", "swmod", "swacc")
            if getattr(field, key)
        ],
        "enums": [[e.name, e.value] for e in field.enums],
    }
