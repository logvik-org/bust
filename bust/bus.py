"""Bus module for bust.

This module is a backward compatibility shim. Import from bust.core.bus instead.
"""

# Re-export from new location for backward compatibility
from bust.core.bus import Bus

__all__ = ["Bus"]
