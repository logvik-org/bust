"""Bus module for bust.

This module defines the Bus class, which represents a bus interface
configuration for VHDL bus slave modules. It supports multiple bus
standards including AXI4-Lite and IPBus.

The Bus class handles bus-specific settings like data width, address width,
reset type, and component library references.
"""

from collections import OrderedDict
from typing import TYPE_CHECKING, Dict

from bust.exceptions import InvalidBusType

if TYPE_CHECKING:
    from bust.core.module import Module


class Bus:
    """Represents a bus interface configuration.

    The Bus class encapsulates all configuration for a specific bus standard,
    including type, data/address widths, and VHDL generation settings. It
    provides methods for generating bus-specific VHDL code.

    Supported bus types:
        - axi: AXI4-Lite (async reset)
        - ipbus: IPBus (sync reset)

    Attributes:
        bus_type: Bus standard identifier ("axi" or "ipbus").
        data_width: Width of data bus in bits.
        addr_width: Width of address bus in bits.
        comp_library: VHDL library name for bus components.
        short_name: Abbreviated bus name for code generation.
        bus_reset: Reset type ("async" or "sync").

    Class Attributes:
        supported_bus: List of supported bus type strings.
        default_comp_library: Default VHDL library ("work").
        default_comp_library_ipbus: Default library for IPBus ("ipbus").
    """

    supported_bus = ["axi", "ipbus"]
    default_comp_library = "work"
    default_comp_library_ipbus = "ipbus"

    def __init__(self, bus: Dict) -> None:
        """Initialize a Bus instance.

        Args:
            bus: Dictionary containing bus configuration with keys:
                - type: Bus type, must be "axi" or "ipbus" (required)
                - data_width: Data bus width in bits (required)
                - addr_width: Address bus width in bits (required)
                - comp_library: VHDL component library (optional, defaults based on type)

        Raises:
            InvalidBusType: If bus type is not in supported_bus list.
        """
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
        """Export bus configuration as an ordered dictionary.

        Returns:
            OrderedDict with bus configuration, omitting comp_library if it
            matches the default value.
        """
        json = OrderedDict()
        json["type"] = self.bus_type
        json["addr_width"] = self.addr_width
        json["data_width"] = self.data_width
        json["reset"] = self.bus_reset
        if self.comp_library != Bus.default_comp_library:
            json["comp_library"] = self.comp_library
        return json
