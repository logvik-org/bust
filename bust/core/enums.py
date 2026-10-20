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

Copyright (c) 2025 Ola Groettvik
Licensed under the Apache License, Version 2.0. See the LICENSE file for details.
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


# The bust 0.14 names of the bit and vector types. bust accepts them for
# registers and fields, and Module warns that they are deprecated.
LEGACY_TYPE_NAMES = {"sl": "bit", "slv": "vector"}


def current_type_name(value):
    """Return `bit` for `sl` and `vector` for `slv`, and any other value as it is."""
    if isinstance(value, str):
        return LEGACY_TYPE_NAMES.get(value.lower(), value)
    return value


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

    Legacy schema. New configs use the per-field `SwAccess`/`HwAccess` model;
    these values are translated onto it (see the compatibility layer).
    """

    RW = "rw"
    RO = "ro"
    PULSE = "pulse"


class SwAccess(ConfigEnum):
    """Software access mode for a field (aligned with SystemRDL 2.0).

    Values:
    - RW: software reads and writes
    - RO: software reads only
    - WO: software writes only (reads return 0)
    - NA: no software access

    Use `SwAccess.from_string(value)` to safely create from user input.
    """

    RW = "rw"
    RO = "ro"
    WO = "wo"
    NA = "na"


class HwAccess(ConfigEnum):
    """Hardware access mode for a field (aligned with SystemRDL 2.0).

    Values:
    - R:  hardware reads the stored value (value out)
    - W:  hardware writes the field (value in, see we/wel)
    - RW: hardware reads and writes
    - NA: no hardware access (software-only register)

    Use `HwAccess.from_string(value)` to safely create from user input.
    """

    R = "r"
    W = "w"
    RW = "rw"
    NA = "na"


class OnRead(ConfigEnum):
    """Software read side effect for a field (aligned with SystemRDL 2.0).

    Values:
    - RCLR: field clears to 0 after a software read
    - RSET: field sets to all 1s after a software read

    Use `OnRead.from_string(value)` to safely create from user input.
    """

    RCLR = "rclr"
    RSET = "rset"


class OnWrite(ConfigEnum):
    """Software write side effect for a field (aligned with SystemRDL 2.0).

    The stored value `f` is combined with the write data `w`:
    - WOSET: `f or w`      (write 1 sets bits)
    - WOCLR: `f and not w`  (write 1 clears bits)
    - WOT:   `f xor w`      (write 1 toggles bits)
    - WZS:   `f or not w`   (write 0 sets bits)
    - WZC:   `f and w`      (write 0 clears bits)
    - WZT:   `f xor not w`  (write 0 toggles bits)
    - WCLR:  all 0s         (any write clears the field)
    - WSET:  all 1s         (any write sets the field)

    Use `OnWrite.from_string(value)` to safely create from user input.
    """

    WOSET = "woset"
    WOCLR = "woclr"
    WOT = "wot"
    WZS = "wzs"
    WZC = "wzc"
    WZT = "wzt"
    WCLR = "wclr"
    WSET = "wset"
