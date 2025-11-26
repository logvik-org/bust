"""VHDL code generator for Bus.

This module is a backward compatibility shim. Import from bust.generators.vhdl.bus_generator instead.
"""

# Re-export from new location for backward compatibility
from bust.generators.vhdl.bus_generator import (
    BusGenerator,
    BusVhdlGenerator,
    BusVHDLGen,
)

__all__ = ["BusGenerator", "BusVhdlGenerator", "BusVHDLGen"]
