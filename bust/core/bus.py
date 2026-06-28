"""Bus module for bust.

This module defines the Bus class, which represents a bus interface
configuration for VHDL bus slave modules. It supports multiple bus
standards including AXI4-Lite and IPBus.

The Bus class handles bus-specific settings like data width, address width,
reset type, and component library references.
"""

from collections import OrderedDict
from typing import Any, Dict

from bust.exceptions import InvalidBusType


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
        byte_addressable: Whether the bus addresses by byte (else by word).
        endpoint_suffix: File-name suffix for the generated endpoint VHDL.

    Class Attributes:
        BUS_CONFIG: Per-bus-type configuration (short name, reset convention,
            forced component library, byte addressing, endpoint file suffix).
        supported_bus: Supported bus type strings (the BUS_CONFIG keys).
        default_comp_library: Default VHDL library ("work") used when no library
            is forced by the bus or supplied in the JSON.
    """

    # One row per supported bus. Adding a single-beat bus is a new entry here
    # plus its endpoint/testbench templates, not edits scattered across methods.
    # comp_library None means "use the JSON value, else default_comp_library".
    BUS_CONFIG: Dict[str, Dict[str, Any]] = {
        "axi": {
            "short_name": "axi",
            "bus_reset": "async",
            "comp_library": None,
            "byte_addressable": True,
            "endpoint_suffix": "axi_endpoint",
        },
        "ipbus": {
            "short_name": "ipb",
            "bus_reset": "sync",
            "comp_library": "ipbus",
            "byte_addressable": False,
            "endpoint_suffix": "ipb_endpoint",
        },
    }
    default_comp_library = "work"
    supported_bus = list(BUS_CONFIG)

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
        if bus["type"] not in Bus.BUS_CONFIG:
            raise InvalidBusType(bus["type"])
        self.bus_type = bus["type"]
        config = Bus.BUS_CONFIG[self.bus_type]

        self.data_width = bus["data_width"]
        self.addr_width = bus["addr_width"]
        self.short_name = config["short_name"]
        self.bus_reset = config["bus_reset"]
        self.byte_addressable = config["byte_addressable"]
        self.endpoint_suffix = config["endpoint_suffix"]

        forced_library = config["comp_library"]
        if forced_library is not None:
            self.comp_library = forced_library
        elif "comp_library" in bus:
            self.comp_library = bus["comp_library"]
        else:
            self.comp_library = Bus.default_comp_library

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
