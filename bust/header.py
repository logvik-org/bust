"""Header file generation module for bust.

This module is a backward compatibility shim. Import from bust.generators.header_generator instead.
"""

# Re-export from new location for backward compatibility
from bust.generators.header_generator import HeaderGenerator, Header

__all__ = ["HeaderGenerator", "Header"]
