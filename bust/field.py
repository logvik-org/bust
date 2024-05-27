from collections import OrderedDict

from bust.utils import add_line_breaks


class Field(object):
    """Documentation for Field"""

    supported_types = ["slv", "sl"]

    def __init__(self, name, sig_type, length, reset, description, pos_low):
        self.name = name
        self.sig_type = sig_type
        self.length = length
        self.reset = reset
        self.description = description
        self.description_with_breaks = add_line_breaks(description, 25)
        self.pos_low = pos_low
        self.pos_high = pos_low + length - 1

    def get_pos_str(self):
        if self.sig_type == "sl":
            return str(self.pos_low)
        elif self.sig_type == "slv":
            return str(self.pos_high) + ":" + str(self.pos_low)

    def get_pos_vhdl(self):
        if self.sig_type == "sl":
            return str(self.pos_low)
        elif self.sig_type == "slv":
            return str(self.pos_high) + " downto " + str(self.pos_low)

    def get_mask(self):
        return pow(2, self.length) - 1 << self.pos_low

    def get_dictionary(self, reset, description):
        dict = OrderedDict()
        dict["name"] = self.name
        dict["type"] = self.sig_type
        dict["length"] = self.length
        if reset:
            dict["reset"] = self.reset
        if description:
            dict["description"] = self.description
        return dict

    def get_table_row(self, num):
        row = [
            num,
            self.name,
            self.sig_type,
            self.get_pos_str,
            self.length,
            self.reset,
            self.description,
        ]
        return row

    def return_dic(self):
        dic = OrderedDict()
        dic["name"] = self.name
        dic["type"] = self.sig_type
        if self.sig_type == "slv":
            dic["length"] = self.length
        if self.reset != "0x0":
            dic["reset"] = self.reset
        if self.description != "":
            dic["description"] = self.description
        return dic
