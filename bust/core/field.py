"""Field module for bust.

This module defines the Field class, which represents an individual bitfield
within a register. Fields can be single-bit (std_logic) or multi-bit
(std_logic_vector) and include position, type, reset value, and validation.

A field is part of a register with type 'fields' and occupies a specific
bit range within the parent register's data width.
"""

import logging
from collections import OrderedDict
from typing import Dict, List, NamedTuple, Optional

from bust.core.enums import FieldType, SwAccess, HwAccess, OnRead, OnWrite
from bust.exceptions import InvalidFieldFormat
from bust.validation.vhdl_validator import is_valid_VHDL
from bust.validation.config_validator import ConfigWrapper


class EnumValue(NamedTuple):
    """A named enumerated value for a field (generates a VHDL enum literal)."""

    name: str
    value: int


# Access-mode properties a field inherits from its register's defaults when the
# field does not set them itself.
INHERITABLE_ACCESS = (
    "sw",
    "hw",
    "onread",
    "onwrite",
    "singlepulse",
    "we",
    "wel",
    "hwset",
    "hwclr",
    "swmod",
    "swacc",
)


class Field:
    """Represents a bitfield within a register.

    A Field is a named range of bits within a register that can be
    individually accessed. Fields support single-bit (bit) or multi-bit (vector)
    types with configurable width, position, and reset values.

    Attributes:
        name: Field name (must be valid VHDL identifier).
        type: Field type (BIT or VECTOR) from FieldType enum.
        width: Bit width of the field.
        reset: Reset value as hex string (e.g., "0x0").
        description: Optional description of the field's purpose.
        pos_low: Lowest bit position within parent register.
        pos_high: Highest bit position within parent register.
        parent_register_name: Name of the containing register.
        mask: Bit mask for extracting this field's value.
    """

    def __init__(
        self,
        field: Dict,
        pos_low: int,
        parent_register_name: str,
        inherited: Optional[Dict] = None,
    ) -> None:
        """Initialize a Field instance.

        Args:
            field: Dictionary containing field configuration with keys:
                - name: Field identifier (required)
                - type: Field type "bit" or "vector" (required)
                - width: Bit width (default: 1)
                - reset: Reset value as hex string (default: "0x0")
                - description: Field description (default: "")
                - sw/hw: software/hardware access modes (inheritable)
                - onread/onwrite: software side effects (inheritable)
                - we/wel/hwset/hwclr/swmod/swacc/singlepulse: modifiers (inheritable)
                - enums: list of {name, value} for an enumerated field
            pos_low: Starting bit position within parent register.
            parent_register_name: Name of parent register for error reporting.
            inherited: Register-level access-mode defaults the field falls back
                to for any property it does not set itself.

        Raises:
            InvalidFieldFormat: If reset value doesn't fit in specified width.
            ValueError: If field name is not a valid VHDL identifier.
        """
        self.logger = logging.getLogger(__name__)

        self.parent_register_name = parent_register_name
        self._inherited = inherited or {}

        self._config = ConfigWrapper(
            field,
            required_keys=["name", "type"],
            defaults={
                "width": 1,
                "reset": "0x0",
                "description": "",
            },
        )

        self.name = self._config.require("name")
        is_valid_VHDL(self.name)

        self.type = FieldType.from_string(self._config.require("type"))
        self.width = self._config.get(
            "width"
        )  # Width can be overridden depending on register type
        self.reset = self._config.get("reset")
        self.description = self._config.get("description")

        # Assign width
        if self.type == FieldType.BIT:
            # Check if the width was explicitly set in the config, and if it matches the module data width
            if self._config.is_set("width") and self._config.get("width") != 1:
                self.logger.warning(
                    f"Field '{self.name}' in register '{self.parent_register_name}' "
                    "has width != 1 for bit type. Forcing width to 1."
                )
            self.width = 1

        self.pos_low = pos_low
        self.pos_high = pos_low + self.width - 1

        # Check that the user-specified reset value is valid
        self.validate_reset_value()

        self._init_access_modes(field)

    def _init_access_modes(self, field: Dict) -> None:
        """Resolve access modes, side effects, modifiers, and enums.

        Each access-mode property is taken from the field if set, otherwise from
        the register-level inherited defaults, otherwise a fallback (sw rw, hw r,
        all modifiers off). SystemRDL-aligned semantics; see enums module.
        """
        self.sw = SwAccess.from_string(self._resolve("sw", "rw"))
        self.hw = HwAccess.from_string(self._resolve("hw", "r"))

        onread = self._resolve("onread", None)
        self.onread = OnRead.from_string(onread) if onread is not None else None
        onwrite = self._resolve("onwrite", None)
        self.onwrite = OnWrite.from_string(onwrite) if onwrite is not None else None

        self.singlepulse = bool(self._resolve("singlepulse", False))
        self.we = bool(self._resolve("we", False))
        self.wel = bool(self._resolve("wel", False))
        self.hwset = bool(self._resolve("hwset", False))
        self.hwclr = bool(self._resolve("hwclr", False))
        self.swmod = bool(self._resolve("swmod", False))
        self.swacc = bool(self._resolve("swacc", False))

        self.enums = self._parse_enums(field.get("enums"))

        self._validate_access_modes()

    def _validate_access_modes(self) -> None:
        """Reject access-mode combinations that have no consistent meaning.

        Grounded in the bust 1.0 spec and the prototype regfile: software side effects
        require the matching software access, hardware write-enables require a
        hardware-writable field, and the two write-behaviour mechanisms
        (`onwrite` and `singlepulse`) are mutually exclusive.
        """
        sw_readable = self.sw in (SwAccess.RW, SwAccess.RO)
        sw_writable = self.sw in (SwAccess.RW, SwAccess.WO)
        hw_writable = self.hw in (HwAccess.W, HwAccess.RW)

        def reject(reason: str) -> None:
            raise InvalidFieldFormat(
                f"{reason} (field {self.name} in reg {self.parent_register_name})"
            )

        if self.sw is SwAccess.NA and self.hw is HwAccess.NA:
            reject("field has neither software nor hardware access")

        if self.we and self.wel:
            reject("we and wel are mutually exclusive")
        if (self.we or self.wel) and not hw_writable:
            reject("we/wel require a hardware-writable field (hw w or rw)")

        if self.onread is not None and not sw_readable:
            reject("onread requires a software-readable field (sw rw or ro)")
        if self.onwrite is not None and not sw_writable:
            reject("onwrite requires a software-writable field (sw rw or wo)")
        if self.onwrite is not None and self.singlepulse:
            reject("onwrite and singlepulse are mutually exclusive")

        if self.singlepulse and not sw_writable:
            reject("singlepulse requires a software-writable field (sw rw or wo)")
        if self.swmod and not sw_writable:
            reject("swmod requires a software-writable field (sw rw or wo)")
        if self.swacc and self.sw is SwAccess.NA:
            reject("swacc requires software access (sw not na)")

    def _resolve(self, key: str, fallback):
        """Field value if set, else inherited register default, else fallback."""
        if self._config.is_set(key):
            return self._config.get(key)
        if key in self._inherited:
            return self._inherited[key]
        return fallback

    def _parse_enums(self, enums) -> List[EnumValue]:
        """Parse and validate the field's enumerated values, if any.

        Raises:
            InvalidFieldFormat: on duplicate names/values or out-of-range values.
        """
        if not enums:
            return []
        parsed: List[EnumValue] = []
        seen_names: List[str] = []
        seen_values: List[int] = []
        maxvalue = (2**self.width) - 1
        for entry in enums:
            name = entry["name"]
            is_valid_VHDL(name)
            if name in seen_names:
                raise InvalidFieldFormat(
                    f"Duplicate enum name '{name}' in field {self.name} "
                    f"in reg {self.parent_register_name}"
                )
            value = int(entry["value"])
            if value < 0 or value > maxvalue:
                raise InvalidFieldFormat(
                    f"Enum '{name}' value {value} does not fit field "
                    f"{self.name} (width {self.width}) in reg "
                    f"{self.parent_register_name}"
                )
            if value in seen_values:
                raise InvalidFieldFormat(
                    f"Duplicate enum value {value} in field {self.name} "
                    f"in reg {self.parent_register_name}"
                )
            seen_names.append(name)
            seen_values.append(value)
            parsed.append(EnumValue(name, value))
        return parsed

    def validate_reset_value(self) -> None:
        """Validate that the reset value fits within the field's bit width.

        Raises:
            InvalidFieldFormat: If reset value exceeds maximum value for width.
        """
        if self._config.is_set("reset"):
            # Check whether reset value matches register width
            # maxvalue is given by 2^width
            maxvalue = (2**self.width) - 1
            if maxvalue < int(self.reset, 16):
                raise InvalidFieldFormat(
                    "Reset value does not match field: "
                    + self.name
                    + " in reg: "
                    + self.parent_register_name
                )

    def get_pos_str(self) -> str:
        """Return bit position as a string for documentation.

        Returns:
            Single bit number for BIT, or "high:low" range for VECTOR.

        Raises:
            ValueError: If field type is not supported.
        """
        if self.type == FieldType.BIT:
            return str(self.pos_low)
        elif self.type == FieldType.VECTOR:
            return str(self.pos_high) + ":" + str(self.pos_low)
        raise ValueError(f"Unsupported field type: {self.type}")

    def get_pos_vhdl(self) -> str:
        """Return bit position as VHDL slice notation.

        Returns:
            Single bit number for BIT, or "high downto low" for VECTOR.

        Raises:
            ValueError: If field type is not supported.
        """
        if self.type == FieldType.BIT:
            return str(self.pos_low)
        elif self.type == FieldType.VECTOR:
            return str(self.pos_high) + " downto " + str(self.pos_low)
        raise ValueError(f"Unsupported field type: {self.type}")

    @property
    def mask(self) -> int:
        """Calculate bit mask for this field within the register.

        Returns:
            Integer mask with bits set for this field's position and width.

        Example:
            For a 4-bit field at position 2, returns 0b00111100 (0x3C).
        """
        return int((pow(2, self.width) - 1) << self.pos_low)

    def return_dic(self) -> OrderedDict:
        """Return field configuration as an ordered dictionary.

        Returns:
            OrderedDict with field configuration, including only non-default
            values for width, reset, and description.
        """
        dic = OrderedDict()
        dic["name"] = self.name
        dic["type"] = self.type.value
        if self.type == FieldType.VECTOR:
            dic["width"] = self.width
        if self.reset != "0x0":
            dic["reset"] = self.reset
        if self.description != "":
            dic["description"] = self.description
        return dic

    @property
    def range_vhdl(self) -> str:
        """Return VHDL range string for the field's internal representation.

        Returns:
            VHDL range in "N-1 downto 0" format for VECTOR fields.

        Raises:
            ValueError: If called on non-VECTOR field type.
        """
        if self.type == FieldType.VECTOR:
            return f"{self.width - 1} downto 0"
        raise ValueError("Only vector fields have a range")

    @property
    def type_vhdl(self) -> str:
        """Return VHDL type declaration for this field.

        Returns:
            "std_logic" for BIT fields, "std_logic_vector(...)" for VECTOR fields.

        Raises:
            ValueError: If field type is not supported.
        """
        if self.type == FieldType.VECTOR:
            return f"std_logic_vector({self.range_vhdl})"
        elif self.type == FieldType.BIT:
            return "std_logic"
        raise ValueError(f"Unsupported field type: {self.type}")

    @property
    def reset_val_vhdl(self) -> str:
        r"""Generate VHDL literal for the field's reset value.

        Returns:
            VHDL literal as string, e.g., "'0'" for BIT, "4X\"F\"" for VECTOR.
        """
        if self.type == FieldType.VECTOR:
            if self.reset == "0x0":
                val = "(others => '0')"
            else:
                val = str(self.width) + 'X"'
                val += format(int(self.reset, 16), "X") + '"'

        elif self.type == FieldType.BIT:
            val = "'" + format(int(self.reset, 16), "X") + "'"

        return val

    @property
    def sw_readable(self) -> bool:
        """True when software can read the field (sw rw or ro)."""
        return self.sw in (SwAccess.RW, SwAccess.RO)

    @property
    def sw_writable(self) -> bool:
        """True when software can write the field (sw rw or wo)."""
        return self.sw in (SwAccess.RW, SwAccess.WO)

    @property
    def hw_readable(self) -> bool:
        """True when hardware can read the field (hw r or rw)."""
        return self.hw in (HwAccess.R, HwAccess.RW)

    @property
    def hw_writable(self) -> bool:
        """True when hardware can write the field's value (hw w or rw)."""
        return self.hw in (HwAccess.W, HwAccess.RW)

    @property
    def holds_state(self) -> bool:
        """True when the field's value can change after reset (gets a t_<reg>_regs member).

        A field needs storage only if something can modify it: a software or
        hardware write, a hardware set/clear, or an onread side effect. A pure
        read-only constant (sw ro, hw r with no side effects) does not.
        """
        return (
            self.sw_writable
            or self.hw_writable
            or self.hwset
            or self.hwclr
            or self.onread is not None
        )

    @property
    def driven_by_hw(self) -> bool:
        """True when hardware writes or strobes the field (it appears in from_hw)."""
        return self.hw_writable or self.hwset or self.hwclr

    @property
    def is_enum(self) -> bool:
        """True when the field carries enumerated values."""
        return bool(self.enums)

    @property
    def enum_type_name(self) -> str:
        """VHDL enum type name generated for an enumerated field."""
        return f"t_{self.parent_register_name}_{self.name}"

    @property
    def value_type_vhdl(self) -> str:
        """Field value type: the enum type when enumerated, else the bit type."""
        return self.enum_type_name if self.is_enum else self.type_vhdl

    @property
    def to_hw_is_record(self) -> bool:
        """True when the to_hw view pairs the value with a strobe (swmod/swacc)."""
        return self.swmod or self.swacc

    @property
    def to_hw_record_name(self) -> str:
        """Per-field to_hw record type name (value + swmod/swacc strobes)."""
        return f"t_{self.parent_register_name}_{self.name}_out"

    @property
    def to_hw_members(self) -> List[str]:
        """Members of the field's to_hw record, value first then strobes."""
        members = ["value"]
        if self.swmod:
            members.append("swmod")
        if self.swacc:
            members.append("swacc")
        return members

    @property
    def from_hw_is_record(self) -> bool:
        """True when the from_hw view needs a record (carries we/wel/set/clr)."""
        return self.we or self.wel or self.hwset or self.hwclr

    @property
    def from_hw_record_name(self) -> str:
        """Per-field from_hw record type name (value + enable/strobe members)."""
        return f"t_{self.parent_register_name}_{self.name}_in"

    @property
    def from_hw_members(self) -> List[str]:
        """Members of the field's from_hw record: value (with we/wel) and set/clr."""
        members: List[str] = []
        if self.hw_writable:
            members.append("value")
            if self.we:
                members.append("we")
            if self.wel:
                members.append("wel")
        if self.hwset:
            members.append("set")
        if self.hwclr:
            members.append("clr")
        return members
