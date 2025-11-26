"""Field module for bust.

This module is a backward compatibility shim. Import from bust.core.field instead.
"""

# Re-export from new location for backward compatibility
from bust.core.field import Field

__all__ = ["Field"]
