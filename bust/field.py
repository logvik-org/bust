from collections import OrderedDict

from bust.utils import add_line_breaks


class Field(object):
    """Documentation for Field"""

    supported_types = ["slv", "sl"]

    def __init__(self, name, type, width, reset, description, pos_low):
        self.name = name
        self.type = type
        self.width = width
        self.reset = reset
        self.description = description
        self.pos_low = pos_low
        self.pos_high = pos_low + width - 1

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

    def get_mask(self):
        return pow(2, self.width) - 1 << self.pos_low

    def get_dictionary(self, reset, description):
        dict = OrderedDict()
        dict["name"] = self.name
        dict["type"] = self.type
        dict["width"] = self.width
        if reset:
            dict["reset"] = self.reset
        if description:
            dict["description"] = self.description
        return dict

    def get_table_row(self, num):
        row = [
            num,
            self.name,
            self.type,
            self.get_pos_str,
            self.width,
            self.reset,
            self.description,
        ]
        return row

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
