"""Field module for bust.

This module defines the Field class, which represents an individual bitfield
within a register. Fields can be single-bit (std_logic) or multi-bit
(std_logic_vector) and include position, type, reset value, and validation.

A field is part of a register with type 'fields' and occupies a specific
bit range within the parent register's data width.
"""

import logging
from collections import OrderedDict
from typing import Dict, List, NamedTuple, Optional, Tuple

from bust.core.enums import FieldType, SwAccess, HwAccess, OnRead, OnWrite
from bust.exceptions import InvalidFieldFormat
from bust.validation.vhdl_validator import is_valid_VHDL
from bust.validation.config_validator import ConfigWrapper, warn_unknown_keys


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


FIELD_KEYS = {
    "name",
    "type",
    "width",
    "position",
    "reset",
    "description",
    "enums",
    *INHERITABLE_ACCESS,
}


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
        # A register without fields is one field with the register's name, which
        # the register has validated already.
        if self.name != parent_register_name:
            is_valid_VHDL(self.name)
        warn_unknown_keys(
            field, FIELD_KEYS, f"field {self.name} of register {parent_register_name}"
        )

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

        # Hardware resets an unset enumerated field to the literal that 0 decodes
        # to, which is the first literal when none has value 0. Headers and docs
        # read `reset`, so it must name that value too.
        if self.is_enum and not self._config.is_set("reset"):
            self.reset = hex(self.reset_state)

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

        self.singlepulse = self._resolve_flag("singlepulse")
        self.we = self._resolve_flag("we")
        self.wel = self._resolve_flag("wel")
        self.hwset = self._resolve_flag("hwset")
        self.hwclr = self._resolve_flag("hwclr")
        self.swmod = self._resolve_flag("swmod")
        self.swacc = self._resolve_flag("swacc")

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

        strobes = self._keys_in_effect(("swmod", "swacc", "singlepulse"))
        if strobes and not self.hw_readable:
            reject(
                f"{', '.join(strobes)} {'is' if len(strobes) == 1 else 'are'} "
                "delivered through to_hw, so the field needs hw r or rw, "
                f"not hw {self.hw.value}"
            )
        # The singlepulse self-clear and a hardware write every cycle both claim
        # the storage each cycle, so the hardware value would be silently dropped.
        if self.singlepulse and self.hw_writes_continuously:
            reject(
                "singlepulse cannot self-clear a field hardware writes every "
                "cycle (hw rw needs we or wel)"
            )
        if self.singlepulse and self.onread is not None:
            reject(
                "onread and singlepulse are mutually exclusive: the field "
                "self-clears, so rclr has no effect and rset fires a pulse on "
                "every read"
            )

        enum_conflicts = self._keys_in_effect(
            ("onread", "onwrite", "singlepulse", "hwset", "hwclr")
        )
        if self.is_enum and enum_conflicts:
            reject(
                f"enums cannot be combined with {', '.join(enum_conflicts)}: "
                "bit-level side effects and hardware set/clear have no meaning "
                "for an enumerated value"
            )

    def _keys_in_effect(self, keys: Tuple[str, ...]) -> List[str]:
        """The access-mode keys among `keys` that are in effect for this field."""
        return [key for key in keys if getattr(self, key) not in (None, False)]

    def _resolve(self, key: str, fallback):
        """Field value if set, else inherited register default, else fallback."""
        if self._config.is_set(key):
            return self._config.get(key)
        if key in self._inherited:
            return self._inherited[key]
        return fallback

    def _resolve_flag(self, key: str) -> bool:
        """Resolve a true/false key. null counts as false."""
        value = self._resolve(key, False)
        if value is None:
            return False
        # bool("false") is True, so a quoted value would silently switch it on.
        if not isinstance(value, bool):
            raise InvalidFieldFormat(
                f"{key} of field {self.name} in reg {self.parent_register_name} "
                f"must be true or false (got {value!r})"
            )
        return value

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
            warn_unknown_keys(
                entry, ("name", "value"), f"enum value {name} of field {self.name}"
            )
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
        # An explicit reset on an enumerated field is only meaningful as one of
        # the named states; otherwise the generated reset silently falls back to
        # the first literal. An unset reset is resolved in __init__ instead.
        if self._config.is_set("reset") and int(self.reset, 16) not in seen_values:
            raise InvalidFieldFormat(
                f"Reset value {self.reset} of enumerated field {self.name} in reg "
                f"{self.parent_register_name} matches no declared enum value"
            )
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
            values for width, reset, and description. Access-mode properties
            and position are included only where the field set them itself, so
            inherited register defaults stay inherited.
        """
        dic = OrderedDict()
        dic["name"] = self.name
        dic["type"] = self.type.value
        if self.type == FieldType.VECTOR:
            dic["width"] = self.width
        if self._config.is_set("position"):
            dic["position"] = self.pos_low
        # The authored reset, so an enum's resolved reset is not written back.
        if self._config.get("reset") != "0x0":
            dic["reset"] = self._config.get("reset")
        for key in INHERITABLE_ACCESS:
            if self._config.is_set(key):
                dic[key] = self._config.get(key)
        if self.enums:
            dic["enums"] = [enum._asdict() for enum in self.enums]
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
            return self.vector_range_vhdl
        raise ValueError("Only vector fields have a range")

    @property
    def vector_range_vhdl(self) -> str:
        """`N-1 downto 0` for any field type, `0 downto 0` for a bit.

        An enumerated field's encoding is a std_logic_vector even when it is one
        bit wide, so its to_slv/decode functions have the same shape either way.
        """
        return f"{self.width - 1} downto 0"

    @property
    def vector_pos_vhdl(self) -> str:
        """Bit position as a `high downto low` slice for any field type.

        Slicing a bit field this way yields a 1-element vector, matching the
        enum encoding functions.
        """
        return f"{self.pos_high} downto {self.pos_low}"

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
    def hw_writes_continuously(self) -> bool:
        """True when hardware writes the field every cycle (hw w/rw, no we/wel)."""
        return self.hw_writable and not self.we and not self.wel

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

    def onwrite_rhs(self, stored: str, wdata: str) -> str:
        """VHDL value the field takes on a software write, per its onwrite effect.

        `stored` is the current-value expression, `wdata` the write-data slice.
        """
        if self.onwrite is None:
            raise ValueError("onwrite_rhs requires a field with an onwrite effect")
        combine = {
            OnWrite.WOSET: f"{stored} or {wdata}",
            OnWrite.WOCLR: f"{stored} and not {wdata}",
            OnWrite.WOT: f"{stored} xor {wdata}",
            OnWrite.WZS: f"{stored} or not {wdata}",
            OnWrite.WZC: f"{stored} and {wdata}",
            OnWrite.WZT: f"{stored} xor not {wdata}",
            OnWrite.WCLR: self.zeros_literal,
            OnWrite.WSET: self.ones_literal,
        }
        return combine[self.onwrite]

    def written_result(self, written: int, stored: Optional[int] = None) -> int:
        """Field-local value a later software read sees after one software write.

        `written` is the field-local write data, `stored` the value before the
        write (the reset value when omitted). A field software cannot write keeps
        `stored`, a singlepulse field has already returned to its reset value, an
        enumerated field holds the decoded literal, and the onwrite effect
        combines `stored` with the write; a field with no effect simply stores
        the written bits. Mirrors the regfile's sw_action for value prediction in
        generated testbenches.
        """
        if stored is None:
            stored = self.reset_state
        mask = (1 << int(self.width)) - 1
        w = written & mask
        if not self.sw_writable:
            return stored
        if self.singlepulse:
            return self.reset_state
        if self.is_enum:
            return self.decoded_value(w)
        if self.onwrite is None:
            return w
        effect = {
            OnWrite.WOSET: stored | w,
            OnWrite.WOCLR: stored & ~w & mask,
            OnWrite.WOT: stored ^ w,
            OnWrite.WZS: stored | (~w & mask),
            OnWrite.WZC: stored & w,
            OnWrite.WZT: stored ^ (~w & mask),
            OnWrite.WCLR: 0,
            OnWrite.WSET: mask,
        }
        return effect[self.onwrite]

    def _decoded_enum(self, bits: int) -> EnumValue:
        """Literal the generated decode yields for `bits`: the matching one, else
        the first (its `when others` arm)."""
        return next((e for e in self.enums if e.value == bits), self.enums[0])

    def decoded_value(self, bits: int) -> int:
        """Encoded value an enumerated field holds after decoding `bits`."""
        return self._decoded_enum(bits).value

    @property
    def reset_state(self) -> int:
        """Field-local value after reset (the decoded literal's value for an enum)."""
        reset = int(self.reset, 16)
        return self.decoded_value(reset) if self.is_enum else reset

    @property
    def pulse_test_value(self) -> int:
        """Field-local write value whose pulse differs from the reset value in
        every bit, so a testbench sees a singlepulse whatever its reset is."""
        return ~self.reset_state & ((1 << int(self.width)) - 1)

    def read_result(self, stored: int) -> int:
        """Field-local value after a software read, accounting for the onread effect."""
        mask = (1 << int(self.width)) - 1
        if self.onread is OnRead.RCLR:
            return 0
        if self.onread is OnRead.RSET:
            return mask
        return stored & mask

    @property
    def zeros_literal(self) -> str:
        """All-zeros literal in the field's bit type (`'0'` or `(others => '0')`)."""
        return "'0'" if self.type == FieldType.BIT else "(others => '0')"

    @property
    def ones_literal(self) -> str:
        """All-ones literal in the field's bit type (`'1'` or `(others => '1')`)."""
        return "'1'" if self.type == FieldType.BIT else "(others => '1')"

    def value_literal(self, value: int) -> str:
        """VHDL literal for `value` in the field's bit type.

        `'1'`/`'0'` for a bit, a sized bit-string (`4x"5"`) for a vector. Used to
        drive a concrete from_hw stimulus in a generated testbench.
        """
        if self.type == FieldType.BIT:
            return "'1'" if value & 1 else "'0'"
        digits = (self.width + 3) // 4
        return f'{self.width}x"{value:0{digits}X}"'

    @property
    def all_ones_literal(self) -> str:
        """All-ones as a sized literal (`'1'` or `4x"F"`), usable as a typed
        expression where the aggregate `ones_literal` would be ambiguous."""
        return self.value_literal((1 << self.width) - 1)

    @property
    def reset_value_vhdl(self) -> str:
        """Reset literal in the field's value type (the enum literal when enumerated)."""
        if not self.is_enum:
            return self.reset_val_vhdl
        return self._decoded_enum(int(self.reset, 16)).name

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
