"""VHDL identifier validation utilities for bust.

This module is a backward compatibility shim. Import from bust.validation.vhdl_validator instead.
"""

# Re-export from new location for backward compatibility
from bust.validation.vhdl_validator import (
    get_identifier,
    is_VHDL_keyword,
    contain_spaces,
    start_with_alphabetic_letter,
    ends_with_underscore,
    contain_two_successive_underscores,
    is_only_alpfanum_,
    is_valid_VHDL,
    is_unique,
    InvalidVHDLIdentifier,
    NonUniqueIdentifer,
)

__all__ = [
    "get_identifier",
    "is_VHDL_keyword",
    "contain_spaces",
    "start_with_alphabetic_letter",
    "ends_with_underscore",
    "contain_two_successive_underscores",
    "is_only_alpfanum_",
    "is_valid_VHDL",
    "is_unique",
    "InvalidVHDLIdentifier",
    "NonUniqueIdentifer",
]
