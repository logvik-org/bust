"""Bus module for bust.

This module defines the Bus class, which represents a bus interface
configuration for VHDL bus slave modules. It supports multiple bus
standards including AXI4-Lite and IPBus.

The Bus class handles bus-specific settings like data width, address width,
reset type, and component library references.
"""

from collections import OrderedDict
from typing import Any, Dict

from bust.exceptions import FormatError, InvalidBusType


class Bus:
    """Represents a bus interface configuration.

    The Bus class encapsulates all configuration for a specific bus standard,
    including type, data/address widths, and VHDL generation settings. It
    provides methods for generating bus-specific VHDL code.

    Supported bus types:
        - axi: AXI4-Lite (async reset)
        - ipbus: IPBus (sync reset)
        - sbi: Simple Bus Interface (sync reset)
        - avalon: Avalon-MM (sync reset)
        - wishbone: Wishbone B4 classic (sync reset)
        - apb: AMBA APB (async active-low reset)

    Attributes:
        bus_type: Bus standard identifier (one of supported_bus).
        data_width: Width of data bus in bits.
        addr_width: Width of address bus in bits.
        comp_library: VHDL library name for bus components.
        short_name: Abbreviated bus name for code generation.
        bus_reset: Reset type ("async" or "sync").
        byte_addressable: Whether the bus addresses by byte (else by word).
        endpoint_suffix: File-name suffix for the generated endpoint VHDL.

    Class Attributes:
        BUS_CONFIG: Per-bus-type configuration (short name, reset convention,
            forced component library, byte addressing, endpoint file suffix,
            widest supported addr_width, fixed data_width).
        supported_bus: Supported bus type strings (the BUS_CONFIG keys).
        default_comp_library: Default VHDL library ("work") used when no library
            is forced by the bus or supplied in the JSON.
    """

    # One row per supported bus. Adding a single-beat bus is a new entry here
    # plus its endpoint/testbench templates, not edits scattered across methods.
    # comp_library None means "use the JSON value, else default_comp_library".
    # max_addr_width None means the protocol's address port follows addr_width.
    # fixed_data_width None means the protocol's data ports follow data_width.
    BUS_CONFIG: Dict[str, Dict[str, Any]] = {
        "axi": {
            "short_name": "axi",
            "bus_reset": "async",
            "comp_library": None,
            "byte_addressable": True,
            "endpoint_suffix": "axi_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "ipbus": {
            "short_name": "ipb",
            "bus_reset": "sync",
            "comp_library": "ipbus",
            "byte_addressable": False,
            "endpoint_suffix": "ipb_endpoint",
            # ipb_addr is a fixed 32-bit port that the endpoint slices to addr_width.
            "max_addr_width": 32,
            # ipb_wdata/ipb_rdata are fixed 32-bit ports wired straight through.
            "fixed_data_width": 32,
        },
        "sbi": {
            "short_name": "sbi",
            "bus_reset": "sync",
            "comp_library": None,
            "byte_addressable": True,
            "endpoint_suffix": "sbi_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "avalon": {
            "short_name": "avalon",
            "bus_reset": "sync",
            "comp_library": None,
            "byte_addressable": True,
            "endpoint_suffix": "avalon_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "wishbone": {
            "short_name": "wishbone",
            "bus_reset": "sync",
            "comp_library": None,
            "byte_addressable": True,
            "endpoint_suffix": "wishbone_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "apb": {
            "short_name": "apb",
            "bus_reset": "async",
            "comp_library": None,
            "byte_addressable": True,
            "endpoint_suffix": "apb_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
    }
    default_comp_library = "work"
    supported_bus = list(BUS_CONFIG)

    def __init__(self, bus: Dict) -> None:
        """Initialize a Bus instance.

        Args:
            bus: Dictionary containing bus configuration with keys:
                - type: Bus type, must be a supported_bus value (required)
                - data_width: Data bus width in bits (required)
                - addr_width: Address bus width in bits (required)
                - comp_library: VHDL component library (optional, defaults based on type)

        Raises:
            InvalidBusType: If bus type is not in supported_bus list.
            FormatError: If addr_width exceeds what the bus protocol carries.
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

        max_addr_width = config["max_addr_width"]
        if max_addr_width is not None and self.addr_width > max_addr_width:
            raise FormatError(
                f"Bus type {self.bus_type} carries {max_addr_width}-bit addresses, "
                f"so addr_width must be at most {max_addr_width} "
                f"(got {self.addr_width})"
            )

        fixed_data_width = config["fixed_data_width"]
        if fixed_data_width is not None and self.data_width != fixed_data_width:
            raise FormatError(
                f"Bus type {self.bus_type} carries {fixed_data_width}-bit data, "
                f"so data_width must be {fixed_data_width} (got {self.data_width})"
            )

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
