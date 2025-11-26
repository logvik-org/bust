"""Factory for creating VHDL generator instances.

This module is a backward compatibility shim. Import from bust.generators.factory instead.
"""

# Re-export from new location for backward compatibility
from bust.generators.factory import GeneratorFactory

__all__ = ["GeneratorFactory"]
