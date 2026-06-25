"""VHDL code generators for bust.

This subpackage contains the VHDL-specific code generators:

- ModuleGenerator: Generates the local-bus VHDL stack and testbenches
"""

from bust.generators.vhdl.module_generator import ModuleGenerator

__all__ = [
    "ModuleGenerator",
]
