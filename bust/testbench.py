"""Testbench generation module for bust.

This module is a backward compatibility shim. Import from bust.generators.testbench_generator instead.
"""

# Re-export from new location for backward compatibility
from bust.generators.testbench_generator import TestbenchGenerator, Testbench

__all__ = ["TestbenchGenerator", "Testbench"]
