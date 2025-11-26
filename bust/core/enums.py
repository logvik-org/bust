"""Strongly typed enumerations for bust.

This module defines strongly typed enumerations used throughout the `bust` tool
for register and field configuration. These enums ensure consistent values and
improve type safety when parsing user configurations via `ConfigWrapper`.

Each enum inherits from `str` and `Enum`, allowing them to behave like strings
while retaining enum benefits such as validation and introspection.

Enums defined:
- FieldType: Types of individual register fields
- RegisterType: Data representation types of full registers
- RegisterMode: Access modes for registers

All enums include a `from_string()` method to safely convert user-provided
strings with validation and case normalization.

Copyright (c) 2025 Grottviq
All rights reserved.
"""

from enum import Enum


class ConfigEnum(Enum):
    """Base class for enumerations for configs."""

    @classmethod
    def from_string(cls, value):
        """Create an enum instance from a string, validating the value."""
        try:
            return cls(value.lower())
        except ValueError as exp:
            raise ValueError(
                f"Invalid {cls.__name__}: '{value}'. Did you mean one of these? {[e.value for e in cls]}"
            ) from exp

    @classmethod
    def valid_values(cls):
        """Return a list of valid enum values as strings."""
        return list(e.value for e in cls)


class FieldType(ConfigEnum):
    """Enumeration of supported field types within a register.

    Values:
    - VECTOR: Multi-bit signal (std_logic_vector)
    - BIT:    Single-bit signal (std_logic)

    Use `FieldType.from_string(value)` to safely create from user input.
    """

    VECTOR = "vector"
    BIT = "bit"


class RegisterType(ConfigEnum):
    """Enumeration of register data types.

    Values:
    - DEFAULT: Matches module data width
    - VECTOR:  std_logic_vector with specified width
    - BIT:     std_logic (single-bit)
    - FIELDS:  Composed of named bitfields

    Use `RegisterType.from_string(value)` to safely create from user input.
    """

    DEFAULT = "default"
    VECTOR = "vector"
    BIT = "bit"
    FIELDS = "fields"


class RegisterMode(ConfigEnum):
    """Enumeration of access modes for a register.

    Values:
    - RW:    Read/write access
    - RO:    Read-only access
    - PULSE: Write-only, single-cycle pulse

    Use `RegisterMode.from_string(value)` to safely create from user input.
    """

    RW = "rw"
    RO = "ro"
    PULSE = "pulse"
