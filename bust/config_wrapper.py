"""Configuration validation utilities for bust.

This module is a backward compatibility shim. Import from bust.validation.config_validator instead.
"""

# Re-export from new location for backward compatibility
from bust.validation.config_validator import ConfigWrapper

__all__ = ["ConfigWrapper"]
