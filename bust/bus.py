from collections import OrderedDict

from bust.bus_vhdl_gen import BusVHDLGen
from bust.exceptions import InvalidBusType


class Bus(object):
    """! @brief Managing bus information"""

    supported_bus = ["axi", "ipbus"]
    default_comp_library = "work"
    default_comp_library_ipbus = "ipbus"

    def __init__(self, bus):
        if bus["type"] in Bus.supported_bus:
            self.bus_type = bus["type"]
        else:
            raise InvalidBusType(bus["type"])

        self.data_width = bus["data_width"]
        self.addr_width = bus["addr_width"]

        if self.bus_type == "ipbus":
            self.comp_library = Bus.default_comp_library_ipbus
        elif "comp_library" in bus:
            self.comp_library = bus["comp_library"]
        else:
            self.comp_library = Bus.default_comp_library

        # Set reset type and short name based on bus
        if self.bus_type == "axi":
            self.short_name = "axi"
            self.bus_reset = "async"
        elif self.bus_type == "ipbus":
            self.short_name = "ipb"
            self.bus_reset = "sync"

    def return_JSON(self):
        json = OrderedDict()
        json["type"] = self.bus_type
        json["addr_width"] = self.addr_width
        json["data_width"] = self.data_width
        json["reset"] = self.bus_reset
        if self.comp_library != Bus.default_comp_library:
            json["comp_library"] = self.comp_library
        return json

    def get_VHDL_generator(self):
        return BusVHDLGen(
            bus_type=self.bus_type,
            comp_library=self.comp_library,
            data_width=self.data_width,
            addr_width=self.addr_width,
        )

    def return_bus_pkg_VHDL(self):
        v_gen = self.get_VHDL_generator()
        return v_gen.return_bus_pkg_VHDL()

    def return_bus_pif_VHDL(self, mod):
        v_gen = self.get_VHDL_generator()
        return v_gen.return_bus_pif_VHDL(mod=mod)
