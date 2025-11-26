import logging
from typing import Dict, List, cast

from bust.exceptions import (
    ModuleDataBitsExceeded,
    UndefinedRegisterType,
    UndefinedFieldType,
    InvalidRegisterFormat,
    InvalidFieldFormat,
    InvalidStallValue,
)
from bust.field import Field
from bust.utils import indent_string
from bust.vhdl_util import is_unique, is_valid_VHDL
from bust.config_wrapper import ConfigWrapper
from bust.enums import RegisterMode, RegisterType


class Register:
    """! @brief Managing register information"""

    def __init__(
        self, reg: Dict, address: int, module_name: str, module_data_width: int
    ) -> None:

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
        elif self.type == RegisterType.SLV:
            pass
        elif self.type == RegisterType.SL:
            # Check if the width was explicitly set in the config, and if it matches the module data width
            if self._config.is_set("width") and self._config.get("width") != 1:
                self.logger.warning(
                    "User-specified width of SL register does not match the expected width (1). Ignoring configured width."
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

    def _init_fields(self) -> None:
        fields = self._config.require("fields")
        for field in fields:
            self.add_field(field)

    def validate_reset_value(self) -> None:
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
        if self.type == RegisterType.SLV:
            return f"{self.width - 1} downto 0"
        raise ValueError("Only slv fields have a range")

    @property
    def type_vhdl(self) -> str:
        if self.type == RegisterType.DEFAULT or (
            self.type == RegisterType.SLV and self.width == self.module_data_width
        ):
            return f"t_{self.module_name}_data"
        elif self.type == RegisterType.SLV:
            return f"std_logic_vector({self.range_vhdl})"
        elif self.type == RegisterType.SL:
            return "std_logic"
        else:
            return f"t_{self.module_name}_{self.mode.value}_{self.name}"

    @property
    def reset_val_vhdl(self) -> str:
        if self.type in [RegisterType.DEFAULT, RegisterType.SLV]:
            if self.reset == "0x0":
                return "(others => '0')"
            else:
                val = str(self.width) + 'X"'
                val += format(int(self.reset, 16), "X") + '"'
                return val
        elif self.type == RegisterType.SL:
            return "'" + format(int(self.reset, 16), "X") + "'"

        raise ValueError(
            "Only default, slv and sl registers can extract reset value directly"
        )

    def add_field(self, field_cfg: Dict) -> None:

        field = Field(field_cfg, self.get_next_pos_low(), self.name)

        # Validate uniqueness of field name
        existing_names = [f.name for f in self.fields]
        is_unique(field.name, existing_names)

        # Increment register width
        self.width += field.width

        # Maintain the register reset value
        reg_reset_int = int(self.reset, 16)
        field_reset_int = int(field.reset, 16)
        reg_reset_int += field_reset_int << field.pos_low
        self.reset = hex(reg_reset_int)

        self.fields.append(field)

    def check_register_data_width(self, module_data_width: int) -> None:
        """! @brief Controls that the combined data bits in fields does not
        exceed data bits of module

        """
        if self.width > module_data_width:
            raise ModuleDataBitsExceeded(self.name, self.width, module_data_width)

    def get_next_pos_low(self) -> int:
        if len(self.fields) > 0:
            last_pos_high: int = self.fields[-1].pos_high
            return last_pos_high + 1
        else:
            return 0

    def get_mode(self) -> str:
        """Get the register mode in r/w/rw format - pulse = w"""
        if self.mode == RegisterMode.PULSE:
            return "w"
        elif self.mode == RegisterMode.RO:
            return "r"
        else:
            return str(self.mode.value)

    def return_stall_string(self) -> str:
        if self.stall:
            return "/STALL"
        else:
            return ""

    def get_stall_cycles_str(self) -> str:
        return str(self.stall_cycles - 2)
