"""Field module for bust.

This module defines the Field class, which represents an individual bitfield
within a register. Fields can be single-bit (std_logic) or multi-bit
(std_logic_vector) and include position, type, reset value, and validation.

A field is part of a register with type 'fields' and occupies a specific
bit range within the parent register's data width.
"""

import logging
from collections import OrderedDict
from typing import Dict

from bust.enums import FieldType
from bust.exceptions import InvalidFieldFormat, UndefinedFieldType
from bust.vhdl_util import is_valid_VHDL
from bust.config_wrapper import ConfigWrapper


class Field(object):
    """Represents a bitfield within a register.

    A Field is a named range of bits within a register that can be
    individually accessed. Fields support single-bit (sl) or multi-bit (slv)
    types with configurable width, position, and reset values.

    Attributes:
        name: Field name (must be valid VHDL identifier).
        type: Field type (SL or SLV) from FieldType enum.
        width: Bit width of the field.
        reset: Reset value as hex string (e.g., "0x0").
        description: Optional description of the field's purpose.
        pos_low: Lowest bit position within parent register.
        pos_high: Highest bit position within parent register.
        parent_register_name: Name of the containing register.
        mask: Bit mask for extracting this field's value.
    """

    def __init__(self, field: Dict, pos_low: int, parent_register_name: str) -> None:
        """Initialize a Field instance.

        Args:
            field: Dictionary containing field configuration with keys:
                - name: Field identifier (required)
                - type: Field type "sl" or "slv" (required)
                - width: Bit width (default: 1)
                - reset: Reset value as hex string (default: "0x0")
                - description: Field description (default: "")
            pos_low: Starting bit position within parent register.
            parent_register_name: Name of parent register for error reporting.

        Raises:
            InvalidFieldFormat: If reset value doesn't fit in specified width.
            ValueError: If field name is not a valid VHDL identifier.
        """

        self.logger = logging.getLogger(__name__)

        self.parent_register_name = parent_register_name

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
        if self.type == FieldType.SL:
            # Check if the width was explicitly set in the config, and if it matches the module data width
            if self._config.is_set("width") and self._config.get("width") != 1:
                self.logger.warning(
                    f"Field '{self.name}' in register '{self.parent_register_name}' "
                    "has width != 1 for sl type. Forcing width to 1."
                )
            self.width = 1

        self.pos_low = pos_low
        self.pos_high = pos_low + self.width - 1

        # Check that the user-specified reset value is valid
        self.validate_reset_value()

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
            Single bit number for SL, or "high:low" range for SLV.

        Raises:
            ValueError: If field type is not supported.
        """
        if self.type == FieldType.SL:
            return str(self.pos_low)
        elif self.type == FieldType.SLV:
            return str(self.pos_high) + ":" + str(self.pos_low)
        raise ValueError(f"Unsupported field type: {self.type}")

    def get_pos_vhdl(self) -> str:
        """Return bit position as VHDL slice notation.

        Returns:
            Single bit number for SL, or "high downto low" for SLV.

        Raises:
            ValueError: If field type is not supported.
        """
        if self.type == FieldType.SL:
            return str(self.pos_low)
        elif self.type == FieldType.SLV:
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
        if self.type == FieldType.SLV:
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
            VHDL range in "N-1 downto 0" format for SLV fields.

        Raises:
            ValueError: If called on non-SLV field type.
        """
        if self.type == FieldType.SLV:
            return f"{self.width - 1} downto 0"
        raise ValueError("Only slv fields have a range")

    @property
    def type_vhdl(self) -> str:
        """Return VHDL type declaration for this field.

        Returns:
            "std_logic" for SL fields, "std_logic_vector(...)" for SLV fields.

        Raises:
            ValueError: If field type is not supported.
        """
        if self.type == FieldType.SLV:
            return f"std_logic_vector({self.range_vhdl})"
        elif self.type == FieldType.SL:
            return "std_logic"
        raise ValueError(f"Unsupported field type: {self.type}")

    @property
    def reset_val_vhdl(self) -> str:
        """Generate VHDL literal for the field's reset value.

        Returns:
            VHDL literal as string, e.g., "'0'" for SL, "4X\"F\"" for SLV.
        """
        if self.type == FieldType.SLV:
            if self.reset == "0x0":
                val = "(others => '0')"
            else:
                val = str(self.width) + 'X"'
                val += format(int(self.reset, 16), "X") + '"'

        elif self.type == FieldType.SL:
            val = "'" + format(int(self.reset, 16), "X") + "'"

        return val
