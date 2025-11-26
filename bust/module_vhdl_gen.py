"""VHDL code generator for Module.

This module is a backward compatibility shim. Import from bust.generators.vhdl.module_generator instead.
"""

# Re-export from new location for backward compatibility
from bust.generators.vhdl.module_generator import (
    ModuleGenerator,
    ModuleVhdlGenerator,
    ModuleVHDLGen,
)

__all__ = ["ModuleGenerator", "ModuleVhdlGenerator", "ModuleVHDLGen"]
