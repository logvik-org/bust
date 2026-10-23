"""Core domain models for bust.

This package contains the core domain classes that represent the fundamental
building blocks of a bus slave module definition:

- Module: Top-level container for a bus slave module
- Bus: Bus interface configuration (AXI, IPBus)
- Register: Memory-mapped register definitions
- Field: Bitfield within a register
- Enums: Strongly typed enumerations for configuration values
"""

from bust.core.module import Module
from bust.core.bus import Bus
from bust.core.register import Register
from bust.core.field import Field
from bust.core.enums import RegisterType, FieldType

__all__ = [
    "Module",
    "Bus",
    "Register",
    "Field",
    "RegisterType",
    "FieldType",
]
