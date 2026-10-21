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
from bust.validation.config_validator import parse_number, warn_unknown_keys


class Bus:
    """Represents a bus interface configuration.

    The Bus class encapsulates all configuration for a specific bus standard,
    including type, data/address widths, and VHDL generation settings. It
    provides methods for generating bus-specific VHDL code.

    Supported bus types:
        - axi: AXI4-Lite
        - ipbus: IPBus
        - sbi: Simple Bus Interface
        - avalon: Avalon-MM
        - wishbone: Wishbone B4 classic
        - apb: AMBA APB

    Attributes:
        bus_type: Bus standard identifier (one of supported_bus).
        data_width: Width of data bus in bits.
        addr_width: Width of address bus in bits.
        byte_addressable: Whether the bus addresses by byte (else by word).
        endpoint_suffix: File-name suffix for the generated endpoint VHDL.

    Class Attributes:
        BUS_CONFIG: Per-bus-type configuration (byte addressing, endpoint file
            suffix, widest supported addr_width, fixed data_width).
        supported_bus: Supported bus type strings (the BUS_CONFIG keys).
    """

    # One row per supported bus. Adding a single-beat bus is a new entry here
    # plus its endpoint/testbench templates, not edits scattered across methods.
    # max_addr_width None means the protocol's address port follows addr_width.
    # fixed_data_width None means the protocol's data ports follow data_width.
    BUS_CONFIG: Dict[str, Dict[str, Any]] = {
        "axi": {
            "byte_addressable": True,
            "endpoint_suffix": "axi_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "ipbus": {
            "byte_addressable": False,
            "endpoint_suffix": "ipb_endpoint",
            # ipb_addr is a fixed 32-bit port that the endpoint slices to addr_width.
            "max_addr_width": 32,
            # ipb_wdata/ipb_rdata are fixed 32-bit ports wired straight through.
            "fixed_data_width": 32,
        },
        "sbi": {
            "byte_addressable": True,
            "endpoint_suffix": "sbi_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "avalon": {
            "byte_addressable": True,
            "endpoint_suffix": "avalon_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "wishbone": {
            "byte_addressable": True,
            "endpoint_suffix": "wishbone_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
        "apb": {
            "byte_addressable": True,
            "endpoint_suffix": "apb_endpoint",
            "max_addr_width": None,
            "fixed_data_width": None,
        },
    }
    supported_bus = list(BUS_CONFIG)

    def __init__(self, bus: Dict) -> None:
        """Initialize a Bus instance.

        Args:
            bus: Dictionary containing bus configuration with keys:
                - type: Bus type, must be a supported_bus value (required)
                - data_width: Data bus width in bits (required)
                - addr_width: Address bus width in bits (required)

        Raises:
            InvalidBusType: If bus type is not in supported_bus list.
            FormatError: If addr_width exceeds what the bus protocol carries.
        """
        if bus["type"] not in Bus.BUS_CONFIG:
            raise InvalidBusType(bus["type"])
        warn_unknown_keys(bus, ("type", "addr_width", "data_width"), "bus")
        self.bus_type = bus["type"]
        config = Bus.BUS_CONFIG[self.bus_type]

        self.data_width = parse_number(bus["data_width"], "data_width of the bus")
        self.addr_width = parse_number(bus["addr_width"], "addr_width of the bus")
        self.byte_addressable = config["byte_addressable"]
        self.endpoint_suffix = config["endpoint_suffix"]

        max_addr_width = config["max_addr_width"]
        if max_addr_width is not None and self.addr_width > max_addr_width:
            raise FormatError(
                f"Bus type {self.bus_type} carries {max_addr_width}-bit addresses, "
                f"so addr_width must be at most {max_addr_width} "
                f"(got {self.addr_width})"
            )

        if self.data_width <= 0 or self.data_width % 8:
            raise FormatError(
                f"data_width must be a whole number of bytes (got {self.data_width})"
            )

        fixed_data_width = config["fixed_data_width"]
        if fixed_data_width is not None and self.data_width != fixed_data_width:
            raise FormatError(
                f"Bus type {self.bus_type} carries {fixed_data_width}-bit data, "
                f"so data_width must be {fixed_data_width} (got {self.data_width})"
            )

    def to_json(self) -> OrderedDict:
        """Export bus configuration as an ordered dictionary.

        Returns:
            OrderedDict with the bus configuration.
        """
        json = OrderedDict()
        json["type"] = self.bus_type
        json["addr_width"] = self.addr_width
        json["data_width"] = self.data_width
        return json
