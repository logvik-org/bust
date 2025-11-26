"""Module management for bus slave generation.

This module is a backward compatibility shim. Import from bust.core.module instead.
"""

# Re-export from new location for backward compatibility
from bust.core.module import Module

__all__ = ["Module"]
