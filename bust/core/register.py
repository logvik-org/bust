"""Register module for bust.

This module defines the Register class, which represents a memory-mapped
register within a bus slave module. Registers can have various types
(default, vector, bit, fields), access modes (RW, RO, PULSE), and optional
features like stall cycles.

Each register has a fixed address, configurable width, reset value, and
can optionally contain multiple named bitfields.
"""

import logging
from typing import Dict, List, cast

from bust.exceptions import (
    ModuleDataBitsExceeded,
    UndefinedRegisterType,
    InvalidRegisterFormat,
    InvalidStallValue,
    InvalidFieldFormat,
)
from bust.core.field import Field
from bust.core.legacy_schema import register_access_defaults
from bust.utils.formatting import indent_string
from bust.validation.vhdl_validator import is_unique, is_valid_VHDL
from bust.validation.config_validator import ConfigWrapper
from bust.core.enums import RegisterMode, RegisterType, SwAccess, HwAccess


class Register:
    """Represents a memory-mapped register in a bus slave module.

    A Register encapsulates all information needed to generate a memory-mapped
    register, including its address, data type, access mode, reset value, and
    optional bitfields. Registers support various modes (read-write, read-only,
    pulse) and types (default width, custom vector, single-bit, or composite fields).

    Attributes:
        name: Register name (must be valid VHDL identifier).
        address: Memory address of the register.
        mode: Access mode (RW, RO, or PULSE).
        type: Data type (DEFAULT, VECTOR, BIT, or FIELDS).
        width: Data width in bits.
        reset: Reset value as hex string.
        description: Optional description of the register's purpose.
        pulse_cycles: Duration of pulse signal for PULSE mode.
        stall_cycles: Number of stall cycles (IPBus only, 2-255).
        stall: True if stall_cycles > 0.
        fields: List of Field objects for FIELDS type registers.
        module_name: Name of parent module.
        module_data_width: Data width of parent module.
    """

    def __init__(
        self, reg: Dict, address: int, module_name: str, module_data_width: int
    ) -> None:
        """Initialize a Register instance.

        Args:
            reg: Dictionary containing register configuration with keys:
                - name: Register identifier (required)
                - mode: Access mode "rw", "ro", or "pulse" (default: "rw")
                - type: Register type "default", "vector", "bit", or "fields" (default: "default")
                - width: Bit width (default: module_data_width)
                - reset: Reset value as hex string (default: "0x0")
                - description: Register description (default: "")
                - pulse_cycles: Pulse duration for PULSE mode (default: 1)
                - stall_cycles: Stall cycles for IPBus (default: 0, range: 0 or 2-255)
                - fields: List of field dictionaries for FIELDS type
            address: Memory address for this register.
            module_name: Name of the parent module.
            module_data_width: Data width of the parent module.

        Raises:
            InvalidRegisterFormat: If reset value doesn't match width or is invalid.
            InvalidStallValue: If stall_cycles is not 0 or between 2-255.
            ModuleDataBitsExceeded: If register width exceeds module data width.
            UndefinedRegisterType: If register type is not supported.
            ValueError: If register name is not a valid VHDL identifier.
        """
        self.logger = logging.getLogger(__name__)

        self.module_name = module_name
        self.module_data_width = module_data_width
        self.address = address
        self.fields: List["Field"] = []

        self._config = ConfigWrapper(
            reg,
            required_keys=["name"],
            defaults={
                "description": "",
                "mode": RegisterMode.RW.value,
                "type": RegisterType.DEFAULT.value,
                "width": module_data_width,
                "reset": "0x0",
                "pulse_cycles": 1,
                "stall_cycles": 0,
            },
        )

        self.name = self._config.require("name")
        is_valid_VHDL(self.name)

        self.description: str = self._config.get("description")
        self.mode = RegisterMode.from_string(self._config.get("mode"))
        self.type = RegisterType.from_string(self._config.get("type"))
        self.width = self._config.get(
            "width"
        )  # Width can be overridden depending on register type
        self.reset = self._config.get("reset")
        self.pulse_cycles = self._config.get("pulse_cycles")
        self.stall_cycles = self._config.get("stall_cycles")
        self.stall = self.stall_cycles > 0

        # If set, stall cycles must be between 2 and 255
        if self.stall:
            if self.stall_cycles < 2 or self.stall_cycles > 255:
                raise InvalidStallValue(self.stall_cycles)

        # bust 1.0 access-mode defaults the register's fields inherit. Legacy `mode`
        # registers are translated onto sw/hw here (see legacy_schema). Fields
        # are constructed below, so this must precede _init_fields.
        self.access_defaults = register_access_defaults(reg)
        self.sw = SwAccess.from_string(self.access_defaults.get("sw", "rw"))
        self.hw = HwAccess.from_string(self.access_defaults.get("hw", "r"))

        # Assign width
        if self.type == RegisterType.DEFAULT:
            # Check if the width was explicitly set in the config,
            # and if it matches the module data width
            if (
                self._config.is_set("width")
                and self._config.get("width") != module_data_width
            ):
                self.logger.warning(
                    f"User-specified width of default register does not match the expected width ({module_data_width}). Ignoring configured width."
                )
            self.width = module_data_width
        elif self.type == RegisterType.VECTOR:
            pass
        elif self.type == RegisterType.BIT:
            # Check if the width was explicitly set in the config, and if it matches the module data width
            if self._config.is_set("width") and self._config.get("width") != 1:
                self.logger.warning(
                    "User-specified width of BIT register does not match the expected width (1). Ignoring configured width."
                )
            self.width = 1

        elif self.type == RegisterType.FIELDS or self._config.is_set("fields"):
            self.width = 0
            self._init_fields()

        else:
            raise UndefinedRegisterType(self.type)

        # Check that the user-specified reset value is valid
        self.validate_reset_value()

        # Perform check that data bits are not exceeded
        self.check_register_data_width(module_data_width)

        self._implicit_field = self._make_implicit_field()

    def _make_implicit_field(self) -> "Field":
        """Synthesize the single full-width field a non-fields register stands for.

        The local-bus generator is field-based, so a `bit`/`vector`/`default`
        register is treated as one field spanning the whole register, named after
        the register and inheriting its access. A register with real fields keeps
        `self.fields` empty here so the legacy generator (which keys off the
        register type) is unaffected.
        """
        if self.fields:  # real fields were parsed (type fields or a `fields` key)
            return None  # type: ignore[return-value]
        field_type = "bit" if self.type == RegisterType.BIT else "vector"
        cfg: Dict = {"name": self.name, "type": field_type, "reset": self.reset}
        if field_type == "vector":
            cfg["width"] = self.width
        return Field(cfg, 0, self.name, inherited=self.access_defaults)

    @property
    def effective_fields(self) -> List["Field"]:
        """Fields for local-bus generation: real fields, or the implicit one."""
        return self.fields if self.fields else [self._implicit_field]

    def _init_fields(self) -> None:
        """Initialize fields from configuration for FIELDS type registers."""
        fields = self._config.require("fields")
        for field in fields:
            self.add_field(field)

    def validate_reset_value(self) -> None:
        """Validate that the reset value fits within the register's bit width.

        Raises:
            InvalidRegisterFormat: If reset value exceeds maximum value for width
                or if reset is specified for record type register.
        """
        if self._config.is_set("reset"):
            # Reset value is not allowed if type is record
            if self.type == "record":
                raise InvalidRegisterFormat(
                    "Reset value is not allowed for record type register: " + self.name
                )

            # Check whether reset value matches register width
            # maxvalue is given by 2^width
            maxvalue = (2**self.width) - 1
            if maxvalue < int(self.reset, 16):
                raise InvalidRegisterFormat(
                    "Reset value does not match register: " + self.name
                )

    def __str__(self) -> str:
        string = "Name: " + self.name + "\n"
        string += "Address: " + hex(self.address) + "\n"
        string += "Mode: " + str(self.mode.value) + "\n"
        string += "Type: " + str(self.type.value) + "\n"
        string += "Width: " + str(self.width) + "\n"
        string += "Reset: " + self.reset
        if self.type == "record":

            for field in self.fields:
                string += "\n"
                string += indent_string(
                    "Name: "
                    + field.name
                    + " Type: "
                    + str(field.type.value)
                    + " Width: "
                    + str(field.width)
                    + " Reset: "
                    + field.reset
                )

        string += "\nDescription: " + self.description + "\n\n"
        return cast(str, string)

    @property
    def range_vhdl(self) -> str:
        """Return VHDL range string for VECTOR registers.

        Returns:
            VHDL range in "N-1 downto 0" format for VECTOR registers.

        Raises:
            ValueError: If called on non-VECTOR register type.
        """
        if self.type == RegisterType.VECTOR:
            return f"{self.width - 1} downto 0"
        raise ValueError("Only vector fields have a range")

    @property
    def type_vhdl(self) -> str:
        """Return VHDL type declaration for this register.

        Returns:
            Type name suitable for VHDL code generation:
            - Module data type for DEFAULT registers
            - std_logic_vector(...) for VECTOR registers
            - std_logic for BIT registers
            - Custom record type for FIELDS registers
        """
        if self.type == RegisterType.DEFAULT or (
            self.type == RegisterType.VECTOR and self.width == self.module_data_width
        ):
            return f"t_{self.module_name}_data"
        elif self.type == RegisterType.VECTOR:
            return f"std_logic_vector({self.range_vhdl})"
        elif self.type == RegisterType.BIT:
            return "std_logic"
        else:
            return f"t_{self.module_name}_{self.mode.value}_{self.name}"

    @property
    def reset_val_vhdl(self) -> str:
        """Generate VHDL literal for the register's reset value.

        Returns:
            VHDL literal as string.

        Raises:
            ValueError: If called on FIELDS type (fields have individual reset values).
        """
        if self.type in [RegisterType.DEFAULT, RegisterType.VECTOR]:
            if self.reset == "0x0":
                return "(others => '0')"
            else:
                val = str(self.width) + 'X"'
                val += format(int(self.reset, 16), "X") + '"'
                return val
        elif self.type == RegisterType.BIT:
            return "'" + format(int(self.reset, 16), "X") + "'"

        raise ValueError(
            "Only default, vector and bit registers can extract reset value directly"
        )

    @property
    def stored_fields(self) -> List[Field]:
        """Fields that hold state (members of t_<reg>_regs)."""
        return [f for f in self.effective_fields if f.holds_state]

    @property
    def to_hw_fields(self) -> List[Field]:
        """Fields the hardware can read (members of t_<reg>_to_hw)."""
        return [f for f in self.effective_fields if f.hw_readable]

    @property
    def from_hw_fields(self) -> List[Field]:
        """Fields the hardware drives or strobes (members of t_<reg>_from_hw)."""
        return [f for f in self.effective_fields if f.driven_by_hw]

    @property
    def enum_fields(self) -> List[Field]:
        """Fields carrying enumerated values."""
        return [f for f in self.effective_fields if f.is_enum]

    @property
    def in_to_hw(self) -> bool:
        """True when at least one field is hardware-readable."""
        return any(f.hw_readable for f in self.effective_fields)

    @property
    def in_from_hw(self) -> bool:
        """True when at least one field is hardware-driven."""
        return any(f.driven_by_hw for f in self.effective_fields)

    @property
    def is_simple_readback(self) -> bool:
        """True when writing a value then reading it returns the same value.

        Holds for a register whose fields are all plain software read-write with no
        side effects, enum encoding, or hardware writer, so a generated testbench can
        write and read it back without modelling access-mode behaviour.
        """
        fields = self.effective_fields
        return bool(fields) and all(
            f.sw is SwAccess.RW
            and not f.is_enum
            and f.onread is None
            and f.onwrite is None
            and not f.singlepulse
            and not f.driven_by_hw
            for f in fields
        )

    @property
    def selftest_value_vhdl(self) -> str:
        """Data-width literal with every field bit set, for readback self-tests."""
        mask = 0
        for f in self.effective_fields:
            mask |= f.mask
        digits = (self.module_data_width + 3) // 4  # ceil: cover non-nibble widths
        return f'{self.module_data_width}x"{mask:0{digits}X}"'

    def add_field(self, field_cfg: Dict) -> None:
        """Add a bitfield to this register.

        Creates a Field object and adds it to the register, updating the
        register's total width and reset value to incorporate the new field.

        Args:
            field_cfg: Dictionary containing field configuration (see Field.__init__).

        Raises:
            ValueError: If field name is not unique within this register.
        """
        next_free = self.get_next_pos_low()
        position = field_cfg.get("position")
        field_name = field_cfg.get("name", "<unknown>")
        if position is None:
            pos_low = next_free
        elif (
            not isinstance(position, int) or isinstance(position, bool) or position < 0
        ):
            raise InvalidFieldFormat(
                f"Field '{field_name}' in register '{self.name}': position must "
                f"be a non-negative integer, got {position!r}."
            )
        elif position < next_free:
            raise InvalidFieldFormat(
                f"Field '{field_name}' in register '{self.name}': position "
                f"{position} overlaps bits already in use (next free bit is "
                f"{next_free})."
            )
        else:
            pos_low = position

        field = Field(
            field_cfg,
            pos_low,
            self.name,
            inherited=self.access_defaults,
        )

        # Validate uniqueness of field name
        existing_names = [f.name for f in self.fields]
        is_unique(field.name, existing_names)

        # Register spans up to its highest field bit, so reserved gaps count.
        self.width = max(self.width, field.pos_high + 1)

        # Maintain the register reset value
        reg_reset_int = int(self.reset, 16)
        field_reset_int = int(field.reset, 16)
        reg_reset_int += field_reset_int << field.pos_low
        self.reset = hex(reg_reset_int)

        self.fields.append(field)

    def check_register_data_width(self, module_data_width: int) -> None:
        """Verify that register width doesn't exceed module data width.

        Args:
            module_data_width: Maximum allowed data width in bits.

        Raises:
            ModuleDataBitsExceeded: If register width exceeds module width.
        """
        if self.width > module_data_width:
            raise ModuleDataBitsExceeded(self.name, self.width, module_data_width)

    def get_next_pos_low(self) -> int:
        """Calculate the next available bit position for adding a field.

        Returns:
            Next free bit position (0 if no fields exist yet).
        """
        if len(self.fields) > 0:
            last_pos_high: int = self.fields[-1].pos_high
            return last_pos_high + 1
        else:
            return 0

    def return_stall_string(self) -> str:
        """Return stall indicator string for documentation.

        Returns:
            "/STALL" if stall is enabled, empty string otherwise.
        """
        if self.stall:
            return "/STALL"
        else:
            return ""

    def get_stall_cycles_str(self) -> str:
        """Return stall cycles count adjusted for VHDL representation.

        Returns:
            String representation of stall_cycles - 2 (VHDL encoding offset).
        """
        return str(self.stall_cycles - 2)
