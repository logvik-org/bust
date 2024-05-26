from bust.exceptions import (
    ModuleDataBitsExceeded,
    UndefinedRegisterType,
    UndefinedFieldType,
    InvalidRegisterFormat,
    InvalidFieldFormat,
    InvalidStallValue,
)
from bust.field import Field
from bust.utils import add_line_breaks, indent_string
from bust.vhdl import is_unique, is_valid_VHDL


class Register:
    """! @brief Managing register information"""

    supported_types = ["default", "slv", "sl"]
    supported_modes = ["RW", "RO", "PULSE"]

    def __init__(self, reg, address, mod_data_length):
        self.name = reg["name"]
        self.mode = reg["mode"].lower()
        self.description = reg["description"]
        self.description_with_breaks = add_line_breaks(reg["description"], 25)
        self.address = address

        if self.mode == "pulse":
            # Check if pulse_cycles is set
            if "pulse_cycles" in reg:
                self.pulse_cycles = reg["pulse_cycles"]
            else:
                self.pulse_cycles = 1

        self.stall = False
        if "stall_cycles" in reg:
            if reg["stall_cycles"] < 2 or reg["stall_cycles"] > 255:
                raise InvalidStallValue(reg["stall_cycles"])
            self.stall = True
            self.stall_cycles = reg["stall_cycles"]

        self.reset = "0x0"
        self.length = 0
        self.fields = []

        if "length" in reg:
            tmp_length = reg["length"]
        else:
            tmp_length = 1  # Setting to 1, in case std_logic

        if "type" in reg:
            self.sig_type = reg["type"]
        else:
            self.sig_type = "fields"

        # Assign the reg type and register data length
        if self.sig_type == "default":
            self.length = mod_data_length

        elif self.sig_type == "slv":
            self.length = tmp_length

        elif self.sig_type == "sl":
            self.sig_type = "sl"

            if tmp_length != 1:
                raise UndefinedRegisterType("SL cannot have length other than 1")
            self.length = tmp_length

        elif self.sig_type == "fields" or "fields" in reg:
            if len(reg["fields"]) > 0:
                for field in reg["fields"]:
                    self.add_field(field)
            else:
                InvalidFieldFormat("Fields are missing in reg: " + self.name)

        else:
            raise UndefinedRegisterType(self.sig_type)

        if "reset" in reg:
            # Reset value is not allowed if sig_type is record
            if self.sig_type == "record":
                raise InvalidRegisterFormat(
                    "Reset value is not allowed for record type register: " + self.name
                )
            else:
                # Check whether reset value matches register length
                # maxvalue is given by 2^length
                maxvalue = (2**self.length) - 1
                if maxvalue < int(reg["reset"], 16):
                    raise InvalidRegisterFormat(
                        "Reset value does not match register: " + self.name
                    )
                else:
                    self.reset = reg["reset"]

        # Perform check that data bits are not exceeded
        self.check_register_data_length(mod_data_length)

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string += "Address: " + hex(self.address) + "\n"
        string += "Mode: " + self.mode + "\n"
        string += "Type: " + self.sig_type + "\n"
        string += "Length: " + str(self.length) + "\n"
        string += "Reset: " + self.reset
        if self.sig_type == "record":

            for i in self.fields:
                string += "\n"
                string += indent_string(
                    "Name: "
                    + i["name"]
                    + " Type: "
                    + i["type"]
                    + " Length: "
                    + str(i["length"])
                    + " Reset: "
                    + i["reset"]
                )

        string += "\nDescription: " + self.description + "\n\n"
        return string

    def add_field(self, field):
        # Check that all required keys exist
        if not all(key in field for key in ("name", "type")):
            raise InvalidFieldFormat(self.name)

        # Make sure field name is valid VHDL
        is_valid_VHDL(field["name"])

        # Make sure the field name is unique in this register
        field_names = [field.name for field in self.fields]
        is_unique(field["name"], field_names)

        if field["type"] == "slv":
            if "length" not in field:
                raise InvalidFieldFormat(self.name)
            length = field["length"]

        elif field["type"] == "sl":
            length = 1

        else:
            raise UndefinedFieldType(field["type"])

        # Increment register length
        self.length += length

        if "reset" in field:
            reset = field["reset"]
            # Check whether reset value matches field length
            # maxvalue is given by 2^length
            maxvalue = (2**length) - 1
            if maxvalue < int(field["reset"], 16):
                raise InvalidFieldFormat(
                    "Reset value does not match field: "
                    + field["name"]
                    + " in reg: "
                    + self.name
                )
        else:
            reset = "0x0"

        if "description" in field:
            description = field["description"]
        else:
            description = ""

        next_low = self.get_next_pos_low()
        self.fields.append(
            Field(field["name"], field["type"], length, reset, description, next_low)
        )

        # Maintain the register reset value
        reg_reset_int = int(self.reset, 16)
        field_reset_int = int(reset, 16)
        reg_reset_int += field_reset_int << next_low
        self.reset = hex(reg_reset_int)

    def check_register_data_length(self, module):
        """! @brief Controls that the combined data bits in fields does not
        exceed data bits of module

        """
        if self.length > module:
            raise ModuleDataBitsExceeded(self.name, self.length, module)

    def get_next_pos_low(self):
        if len(self.fields) > 0:
            last_pos_high = self.fields[-1].pos_high
            return last_pos_high + 1
        else:
            return 0

    def get_mode(self):
        """Get the register mode in r/w/rw format - pulse = w"""
        if self.mode == "pulse":
            return "w"
        elif self.mode == "ro":
            return "r"
        else:
            return self.mode

    def return_stall_string(self):
        if self.stall:
            return "/STALL"
        else:
            return ""

    def get_stall_cycles_str(self):
        return str(self.stall_cycles - 2)
