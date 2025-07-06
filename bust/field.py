import logging
from collections import OrderedDict

from bust.enums import FieldType
from bust.exceptions import InvalidFieldFormat, UndefinedFieldType
from bust.vhdl_util import is_valid_VHDL
from bust.config_wrapper import ConfigWrapper


class Field(object):
    """Documentation for Field"""

    def __init__(self, field, pos_low, parent_register_name):

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
        if self.type == "sl":
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

    def validate_reset_value(self):
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

    def get_pos_str(self):
        if self.type == "sl":
            return str(self.pos_low)
        elif self.type == "slv":
            return str(self.pos_high) + ":" + str(self.pos_low)

    def get_pos_vhdl(self):
        if self.type == "sl":
            return str(self.pos_low)
        elif self.type == "slv":
            return str(self.pos_high) + " downto " + str(self.pos_low)

    @property
    def mask(self):
        return pow(2, self.width) - 1 << self.pos_low

    def return_dic(self):
        dic = OrderedDict()
        dic["name"] = self.name
        dic["type"] = self.type
        if self.type == "slv":
            dic["width"] = self.width
        if self.reset != "0x0":
            dic["reset"] = self.reset
        if self.description != "":
            dic["description"] = self.description
        return dic

    @property
    def range_vhdl(self):
        if self.type == "slv":
            return f"{self.width - 1} downto 0"
        raise ValueError("Only slv fields have a range")

    @property
    def type_vhdl(self):
        if self.type == "slv":
            return f"std_logic_vector({self.range_vhdl})"
        elif self.type == "sl":
            return "std_logic"

    @property
    def reset_val_vhdl(self):
        if self.type == "slv":
            if self.reset == "0x0":
                val = "(others => '0')"
            else:
                val = str(self.width) + 'X"'
                val += format(int(self.reset, 16), "X") + '"'

        elif self.type == "sl":
            val = "'" + format(int(self.reset, 16), "X") + "'"

        return val
