"""Register module for bust.

This module is a backward compatibility shim. Import from bust.core.register instead.
"""

# Re-export from new location for backward compatibility
from bust.core.register import Register

__all__ = ["Register"]
