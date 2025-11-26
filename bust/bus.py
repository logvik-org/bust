from collections import OrderedDict
from typing import TYPE_CHECKING, Dict

from bust.bus_vhdl_gen import BusVHDLGen
from bust.exceptions import InvalidBusType

if TYPE_CHECKING:
    from bust.module import Module


class Bus:
    """! @brief Managing bus information"""

    supported_bus = ["axi", "ipbus"]
    default_comp_library = "work"
    default_comp_library_ipbus = "ipbus"

    def __init__(self, bus: Dict) -> None:
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

    def to_json(self) -> OrderedDict:
        """Convert bus configuration to JSON-serializable OrderedDict."""
        json = OrderedDict()
        json["type"] = self.bus_type
        json["addr_width"] = self.addr_width
        json["data_width"] = self.data_width
        json["reset"] = self.bus_reset
        if self.comp_library != Bus.default_comp_library:
            json["comp_library"] = self.comp_library
        return json

    def return_JSON(self) -> OrderedDict:
        """Deprecated: Use to_json() instead."""
        return self.to_json()

    def create_vhdl_generator(self) -> BusVHDLGen:
        """Create and return a VHDL generator for this bus."""
        return BusVHDLGen(
            bus_type=self.bus_type,
            comp_library=self.comp_library,
            data_width=self.data_width,
            addr_width=self.addr_width,
        )

    def get_VHDL_generator(self) -> BusVHDLGen:
        """Deprecated: Use create_vhdl_generator() instead."""
        return self.create_vhdl_generator()

    def generate_bus_package_vhdl(self) -> str:
        """Generate VHDL package for the bus."""
        v_gen = self.create_vhdl_generator()
        return v_gen.generate_bus_package_vhdl()

    def return_bus_pkg_VHDL(self) -> str:
        """Deprecated: Use generate_bus_package_vhdl() instead."""
        return self.generate_bus_package_vhdl()

    def generate_bus_pif_vhdl(self, mod: "Module") -> str:
        """Generate VHDL PIF (Physical Interface) for the bus."""
        v_gen = self.create_vhdl_generator()
        return v_gen.generate_bus_pif_vhdl(mod=mod)

    def return_bus_pif_VHDL(self, mod: "Module") -> str:
        """Deprecated: Use generate_bus_pif_vhdl() instead."""
        return self.generate_bus_pif_vhdl(mod)
