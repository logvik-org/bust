"""Register module for bust.

This module defines the Register class, which represents a memory-mapped
register within a bus slave module. Registers can have various types
(default, vector, bit, fields) and access modes (RW, RO, PULSE).

Each register has a fixed address, configurable width, reset value, and
can optionally contain multiple named bitfields.
"""

import logging
from collections import OrderedDict
from typing import Any, Dict, List, Optional, cast

from bust.exceptions import (
    ModuleDataBitsExceeded,
    UndefinedRegisterType,
    InvalidRegisterFormat,
    InvalidFieldFormat,
)
from bust.core.field import Field
from bust.core.legacy_schema import (
    register_access_defaults,
    reject_unsupported_timing,
    uses_new_schema,
)
from bust.utils.formatting import indent_string
from bust.validation.vhdl_validator import is_unique, is_valid_VHDL
from bust.validation.config_validator import ConfigWrapper
from bust.core.enums import OnRead, RegisterMode, RegisterType, SwAccess, HwAccess

# Register-level access summarised from its fields, keyed by
# (any field readable, any field writable).
_SW_BY_READ_WRITE = {
    (True, True): SwAccess.RW,
    (True, False): SwAccess.RO,
    (False, True): SwAccess.WO,
    (False, False): SwAccess.NA,
}
_HW_BY_READ_WRITE = {
    (True, True): HwAccess.RW,
    (True, False): HwAccess.R,
    (False, True): HwAccess.W,
    (False, False): HwAccess.NA,
}


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
                - pulse_cycles: Legacy pulse duration, accepted only as 1
                - stall_cycles: Legacy IPBus stall, accepted only as 0
                - fields: List of field dictionaries for FIELDS type
            address: Memory address for this register.
            module_name: Name of the parent module.
            module_data_width: Data width of the parent module.

        Raises:
            InvalidRegisterFormat: If reset value doesn't match width or is invalid,
                or pulse_cycles/stall_cycles ask for timing bust 1.0 cannot honour.
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
                "type": (
                    RegisterType.FIELDS.value
                    if "fields" in reg
                    else RegisterType.DEFAULT.value
                ),
                "width": module_data_width,
                "reset": "0x0",
            },
        )

        self.name = self._config.require("name")
        is_valid_VHDL(self.name)
        reject_unsupported_timing(reg)

        self.description: str = self._config.get("description")
        self.mode = RegisterMode.from_string(self._config.get("mode"))
        self.uses_new_schema = uses_new_schema(reg)
        # The legacy `mode` and the bust 1.0 `sw`/`hw` keys are two ways to say the
        # same thing; honoring one and silently dropping the other hides intent.
        if self._config.is_set("mode") and self.uses_new_schema:
            raise InvalidRegisterFormat(
                f"Register {self.name} sets the legacy 'mode' key together with "
                "bust 1.0 access-mode keys (sw/hw/...); use one schema, not both"
            )
        self.type = RegisterType.from_string(self._config.get("type"))
        if self._config.is_set("fields") and self.type != RegisterType.FIELDS:
            raise InvalidRegisterFormat(
                f"Register {self.name} has fields but type '{self.type.value}'. "
                "Use type 'fields' or remove the fields."
            )
        self.width = self._config.get(
            "width"
        )  # Width can be overridden depending on register type
        self.reset = self._config.get("reset")

        # bust 1.0 access-mode defaults the register's fields inherit. Legacy `mode`
        # registers are translated onto sw/hw here (see legacy_schema). Fields
        # are constructed below, so this must precede _init_fields.
        self.access_defaults = register_access_defaults(reg)

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

        elif self.type == RegisterType.FIELDS:
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
        if not fields:
            raise InvalidRegisterFormat(f"Register {self.name} has no fields")
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

    def to_json(self, include_address: bool = False) -> OrderedDict:
        """Export the register configuration in the schema it was authored in.

        A legacy register keeps its `mode`. A bust 1.0 register keeps its
        register-level access defaults, and each field keeps only the properties
        it set itself, so re-parsing reproduces the same inheritance.

        Args:
            include_address: Whether to include the register's address.

        Returns:
            OrderedDict accepted by Register.__init__.
        """
        dic: OrderedDict = OrderedDict()
        dic["name"] = self.name
        if self._config.is_set("mode"):
            dic["mode"] = self.mode.value
        elif self.uses_new_schema:
            dic.update(self.access_defaults)
        # Only the no-op values (pulse_cycles 1, stall_cycles 0) get this far.
        if self._config.is_set("pulse_cycles"):
            dic["pulse_cycles"] = self._config.get("pulse_cycles")
        dic["type"] = self.type.value
        if include_address:
            dic["address"] = hex(self.address)
        if self.type == RegisterType.VECTOR:
            dic["width"] = self.width
        if self.type != RegisterType.FIELDS:
            dic["reset"] = self.reset
        if self._config.is_set("stall_cycles"):
            dic["stall_cycles"] = self._config.get("stall_cycles")
        if self.type == RegisterType.FIELDS:
            dic["fields"] = [field.return_dic() for field in self.fields]
        dic["description"] = self.description
        return dic

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
    def sw(self) -> SwAccess:
        """Effective software access: readable if any field is, writable if any is.

        Taken from the fields, not the register-level default, because fields can
        override that default or carry the only access keys in the register.
        """
        fields = self.effective_fields
        return _SW_BY_READ_WRITE[
            (any(f.sw_readable for f in fields), any(f.sw_writable for f in fields))
        ]

    @property
    def hw(self) -> HwAccess:
        """Effective hardware access: readable if any field is, writable if any is."""
        fields = self.effective_fields
        return _HW_BY_READ_WRITE[
            (any(f.hw_readable for f in fields), any(f.hw_writable for f in fields))
        ]

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
    def swmod_fields(self) -> List[Field]:
        """Fields that pulse a swmod strobe when software modifies them."""
        return [f for f in self.effective_fields if f.swmod]

    @property
    def swacc_fields(self) -> List[Field]:
        """Fields that pulse a swacc strobe when software accesses them."""
        return [f for f in self.effective_fields if f.swacc]

    @property
    def singlepulse_fields(self) -> List[Field]:
        """Fields that drive the hardware for a single cycle after a write."""
        return [f for f in self.effective_fields if f.singlepulse]

    @property
    def has_strobes(self) -> bool:
        """True when a field emits a swmod/swacc/singlepulse to_hw strobe."""
        return bool(self.swmod_fields or self.swacc_fields or self.singlepulse_fields)

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
        return self._data_width_literal(mask)

    def _data_width_literal(self, value: int) -> str:
        digits = (self.module_data_width + 3) // 4  # ceil: cover non-nibble widths
        return f'{self.module_data_width}x"{value:0{digits}X}"'

    @property
    def reads_back_zero(self) -> bool:
        """True when a software read returns 0 after a write: write-only fields,
        and singlepulse fields that return to a reset value of 0."""
        fields = self.effective_fields
        return (
            bool(fields)
            and any(f.sw_writable for f in fields)
            and all(
                (not f.sw_readable or (f.singlepulse and f.reset_state == 0))
                and f.onread is None
                and f.onwrite is None
                and not f.is_enum
                and not f.driven_by_hw
                for f in fields
            )
        )

    @property
    def is_enum_readback(self) -> bool:
        """Single plain read-write enum field: write a valid encoding and read it back."""
        fields = self.effective_fields
        return (
            len(fields) == 1
            and fields[0].is_enum
            and fields[0].sw is SwAccess.RW
            and fields[0].onread is None
            and fields[0].onwrite is None
            and not fields[0].singlepulse
            and not fields[0].driven_by_hw
        )

    @property
    def enum_selftest_value_vhdl(self) -> str:
        """Data-width literal encoding the field's highest defined enum value."""
        if not self.is_enum_readback:
            raise ValueError(
                f"enum_selftest_value_vhdl is only valid for a single plain "
                f"read-write enum register (register '{self.name}')"
            )
        field = self.effective_fields[0]
        value = max(e.value for e in field.enums) << field.pos_low
        return self._data_width_literal(value)

    @staticmethod
    def _alternating_bits(width: int) -> int:
        """0b0101… within `width` bits: a mix of set and clear bits so set, clear,
        and toggle write/read effects each produce an observable change."""
        value = 0
        for bit in range(0, width, 2):
            value |= 1 << bit
        return value

    def _register_value(self, field_value) -> int:
        """OR each field's contribution into a full-register value.

        `field_value(field)` returns the field-local integer, shifted here to the
        field's position.
        """
        value = 0
        for f in self.effective_fields:
            value |= field_value(f) << f.pos_low
        return value

    def _require_predictable(self, condition: bool, prop: str, kind: str) -> None:
        if not condition:
            raise ValueError(
                f"{prop} is only valid for a {kind} register (register '{self.name}')"
            )

    @property
    def is_onwrite_readback(self) -> bool:
        """Plain rw register whose readback after one write is a pure function of the
        write value: onwrite side effects only, no read effect or hardware writer."""
        fields = self.effective_fields
        return (
            bool(fields)
            and any(f.onwrite is not None for f in fields)
            and all(
                f.sw is SwAccess.RW
                and f.onread is None
                and not f.singlepulse
                and not f.is_enum
                and not f.driven_by_hw
                for f in fields
            )
        )

    @property
    def onwrite_write_value_vhdl(self) -> str:
        """Data-width literal of the stimulus written to an onwrite register."""
        self._require_predictable(
            self.is_onwrite_readback, "onwrite_write_value_vhdl", "write-effect"
        )
        return self._data_width_literal(
            self._register_value(lambda f: self._alternating_bits(f.width))
        )

    @property
    def onwrite_expected_value_vhdl(self) -> str:
        """Data-width literal read back after the onwrite stimulus is applied."""
        self._require_predictable(
            self.is_onwrite_readback, "onwrite_expected_value_vhdl", "write-effect"
        )
        return self._data_width_literal(
            self._register_value(
                lambda f: f.written_result(self._alternating_bits(f.width))
            )
        )

    @property
    def is_onread_readback(self) -> bool:
        """Plain rw register whose value after a read is a pure function of the
        stored value: onread side effects only, no write effect or hardware writer."""
        fields = self.effective_fields
        return (
            bool(fields)
            and any(f.onread is not None for f in fields)
            and all(
                f.sw is SwAccess.RW
                and f.onwrite is None
                and not f.singlepulse
                and not f.is_enum
                and not f.driven_by_hw
                for f in fields
            )
        )

    @property
    def onread_write_value_vhdl(self) -> str:
        """Data-width literal written to an onread register (also its first readback,
        since these fields store the written value before the read effect)."""
        self._require_predictable(
            self.is_onread_readback, "onread_write_value_vhdl", "read-effect"
        )
        return self._data_width_literal(
            self._register_value(lambda f: self._alternating_bits(f.width))
        )

    @property
    def onread_post_read_value_vhdl(self) -> str:
        """Data-width literal returned by a second read, after the onread effect."""
        self._require_predictable(
            self.is_onread_readback, "onread_post_read_value_vhdl", "read-effect"
        )
        return self._data_width_literal(
            self._register_value(
                lambda f: f.read_result(self._alternating_bits(f.width))
            )
        )

    @property
    def is_hw_driven_readback(self) -> bool:
        """Pure hardware status register: software-readonly fields driven entirely
        by hardware value inputs, so driving from_hw and reading back over the bus
        is fully predictable. Excludes hwset/hwclr-only and software-writable fields
        (their sequencing is covered separately)."""
        fields = self.effective_fields
        return bool(fields) and all(
            f.sw is SwAccess.RO
            and f.hw_writable
            and not f.hwset
            and not f.hwclr
            and f.onread is None
            and f.onwrite is None
            and not f.is_enum
            for f in fields
        )

    @property
    def hw_driven_expected_value_vhdl(self) -> str:
        """Data-width literal read back after the from_hw stimulus is driven."""
        self._require_predictable(
            self.is_hw_driven_readback,
            "hw_driven_expected_value_vhdl",
            "hardware-driven status",
        )
        return self._data_width_literal(
            self._register_value(lambda f: self._alternating_bits(f.width))
        )

    @property
    def hw_drive_steps(self) -> List[Dict[str, Optional[str]]]:
        """Per-field from_hw stimulus for a hardware-driven status register: the
        target member, its enable strobe (we/wel/none), and the value literal."""
        self._require_predictable(
            self.is_hw_driven_readback, "hw_drive_steps", "hardware-driven status"
        )
        steps: List[Dict[str, Optional[str]]] = []
        for f in self.from_hw_fields:
            steps.append(
                {
                    "field": f.name,
                    "member": "value" if f.from_hw_is_record else None,
                    "enable": "we" if f.we else ("wel" if f.wel else None),
                    "literal": f.value_literal(self._alternating_bits(f.width)),
                }
            )
        return steps

    @property
    def is_hw_modify_register(self) -> bool:
        """Software-writable, hardware-readable register exercising hardware value
        overrides (we) and/or hardware set/clear (hwset/hwclr). Its readback is
        predictable through a fixed sw-write -> we-override -> hwset -> hwclr
        scenario. Hardware-writable fields must gate on we (no continuous write
        racing software)."""
        fields = self.effective_fields
        if not fields or not any(f.we or f.hwset or f.hwclr for f in fields):
            return False
        return all(
            f.sw is SwAccess.RW
            and f.hw_readable
            and f.onread is None
            and f.onwrite is None
            and not f.singlepulse
            and not f.is_enum
            and not f.swmod
            and not f.swacc
            and not f.wel
            and (f.we if f.hw_writable else True)
            for f in fields
        )

    @property
    def is_hwset_read_clear_register(self) -> bool:
        """Single sticky field (hwset, onread rclr, swacc) with no hardware value
        write. Its swacc strobe is high in the cycle after a read clear, so a
        testbench holding hwset through a read can sample there whether the set
        or the clear won that cycle, without knowing the bus timing."""
        fields = self.effective_fields
        return (
            len(fields) == 1
            and fields[0].hwset
            and fields[0].onread is OnRead.RCLR
            and fields[0].swacc
            and not fields[0].hw_writable
        )

    def _hw_input_during_selftest(self, f: Field) -> int:
        """from_hw value the generated testbench holds on a hardware-written field.

        The hardware-driven status test leaves its stimulus applied; otherwise the
        input sits at its declared default (localbus_tb/hw_signals.j2): zero, or the
        reset literal for an enum.
        """
        if self.is_hw_driven_readback:
            return self._alternating_bits(f.width)
        return f.reset_state if f.is_enum else 0

    def _value_before_strobe_test(self, f: Field) -> int:
        """Field-local value the earlier self-tests leave in `f`.

        The earlier test categories are mutually exclusive, and the hardware-modify
        one never covers a strobe register, so at most one has written this
        register; otherwise the field still holds its reset value.
        """
        alternating = self._alternating_bits(f.width)
        if f.hw_writes_continuously:
            return self._hw_input_during_selftest(f)
        if self.is_simple_readback:
            return (1 << int(f.width)) - 1
        if self.is_enum_readback:
            return max(e.value for e in f.enums)
        if self.is_onwrite_readback:
            return f.written_result(alternating)
        if self.is_onread_readback:
            return f.read_result(alternating)
        if self.is_hw_driven_readback:
            return alternating
        return f.reset_state

    @staticmethod
    def _strobe_write(f: Field) -> int:
        """Field-local value the strobe test writes: every bit set, except that a
        singlepulse field gets the inverse of its reset so its pulse is visible."""
        return f.pulse_test_value if f.singlepulse else (1 << int(f.width)) - 1

    @property
    def strobe_write_value_vhdl(self) -> str:
        """Data-width literal the strobe test writes (see _strobe_write)."""
        return self._data_width_literal(self._register_value(self._strobe_write))

    @property
    def strobe_readback_value_vhdl(self) -> str:
        """Data-width literal the strobe test reads back after its write.

        Each field starts from what the earlier self-tests left in it and takes the
        write through its own write predictor, so onwrite effects, enum decoding,
        a singlepulse returning to its reset value and read-only fields in the
        same register are all accounted for. A field hardware writes every cycle
        shows its from_hw input again by the time of the read.
        """

        def readback(f: Field) -> int:
            if not f.sw_readable:
                return 0
            before = self._value_before_strobe_test(f)
            if f.hw_writes_continuously:
                return before
            return f.written_result(self._strobe_write(f), before)

        return self._data_width_literal(self._register_value(readback))

    def _compose(self, state: Dict[str, int]) -> int:
        """Pack a per-field value map into a full register value."""
        value = 0
        for f in self.effective_fields:
            mask = (1 << f.width) - 1
            value |= (state[f.name] & mask) << f.pos_low
        return value

    @property
    def hw_modify_steps(self) -> List[Dict[str, Any]]:
        """Ordered scenario for a hardware-modify register: software baseline,
        then hardware we override, hwset, and hwclr (clr beats set). Each step
        carries the from_hw drives/strobes to apply and the expected readback."""
        self._require_predictable(
            self.is_hw_modify_register, "hw_modify_steps", "hardware-modify"
        )
        fields = self.effective_fields
        state = {f.name: self._alternating_bits(f.width) for f in fields}
        steps: List[Dict[str, Any]] = []

        steps.append(
            {
                "log": f"{self.name}: software baseline write",
                "sw_write": self._data_width_literal(self._compose(state)),
                "drives": [],
                "strobes": [],
                "expected": self._data_width_literal(self._compose(state)),
                "expected_msg": f"{self.name} reads back the software value",
                "to_hw_checks": [
                    {
                        "target": f.name + (".value" if f.to_hw_is_record else ""),
                        "literal": f.value_literal(state[f.name]),
                        "name": f.name,
                    }
                    for f in fields
                    if f.hw_readable
                ],
            }
        )

        we_fields = [f for f in fields if f.we]
        if we_fields:
            for f in we_fields:
                state[f.name] = (~self._alternating_bits(f.width)) & (
                    (1 << f.width) - 1
                )
            steps.append(
                {
                    "log": f"{self.name}: hardware we overrides the stored value",
                    "sw_write": None,
                    "drives": [
                        {
                            "target": f.name + ".value",
                            "literal": f.value_literal(state[f.name]),
                        }
                        for f in we_fields
                    ],
                    "strobes": [
                        {"target": f.name + ".we", "on": "'1'", "off": "'0'"}
                        for f in we_fields
                    ],
                    "expected": self._data_width_literal(self._compose(state)),
                    "expected_msg": f"{self.name} reflects the hardware we override",
                    "to_hw_checks": [],
                }
            )

        hwset_fields = [f for f in fields if f.hwset]
        if hwset_fields:
            for f in hwset_fields:
                state[f.name] = (1 << f.width) - 1
            steps.append(
                {
                    "log": f"{self.name}: hwset drives fields high",
                    "sw_write": None,
                    "drives": [],
                    "strobes": [
                        {"target": f.name + ".set", "on": "'1'", "off": "'0'"}
                        for f in hwset_fields
                    ],
                    "expected": self._data_width_literal(self._compose(state)),
                    "expected_msg": f"{self.name} reflects hwset",
                    "to_hw_checks": [],
                }
            )

        hwclr_fields = [f for f in fields if f.hwclr]
        if hwclr_fields:
            strobes = []
            for f in hwclr_fields:
                state[f.name] = 0
                if f.hwset:  # assert set in the same cycle: clr must win
                    strobes.append(
                        {"target": f.name + ".set", "on": "'1'", "off": "'0'"}
                    )
                strobes.append({"target": f.name + ".clr", "on": "'1'", "off": "'0'"})
            steps.append(
                {
                    "log": f"{self.name}: hwclr clears fields (and beats hwset)",
                    "sw_write": None,
                    "drives": [],
                    "strobes": strobes,
                    "expected": self._data_width_literal(self._compose(state)),
                    "expected_msg": f"{self.name} reflects hwclr",
                    "to_hw_checks": [],
                }
            )

        return steps

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
