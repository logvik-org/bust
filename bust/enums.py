"""Strongly typed enumerations for bust.

This module is a backward compatibility shim. Import from bust.core.enums instead.
"""

# Re-export from new location for backward compatibility
from bust.core.enums import (
    ConfigEnum,
    FieldType,
    RegisterType,
    RegisterMode,
)

__all__ = [
    "ConfigEnum",
    "FieldType",
    "RegisterType",
    "RegisterMode",
]
