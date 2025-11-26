"""bust - Bus Utility for Simplified VHDL.

bust is a Python tool for creating and modifying VHDL bus slave modules.
It generates complete VHDL code including register interfaces, testbenches,
documentation, and language-specific header files from simple JSON configuration.

Supported bus standards:
    - AXI4-Lite
    - IPBus

Main components:
    - Module: Bus slave module definition
    - Register: Individual register configuration
    - Field: Bitfield within a register
    - Bus: Bus interface configuration
    - Header: Language header file generation
    - Documentation: LaTeX documentation generation
    - Testbench: UVVM testbench generation

Package structure:
    - core: Domain models (Module, Bus, Register, Field, Enums)
    - generators: Code generation (VHDL, headers, documentation, testbenches)
    - validation: VHDL identifier and configuration validation
    - utils: File I/O, JSON parsing, and string formatting utilities
    - jinja_utils: Jinja2 template utilities
"""

# Import core domain classes for convenience
from bust.core import (
    Module,
    Bus,
    Register,
    Field,
    RegisterMode,
    RegisterType,
    FieldType,
)

# Import generator classes
from bust.generators import (
    HeaderGenerator,
    DocumentationGenerator,
    TestbenchGenerator,
    GeneratorFactory,
)

# Backward compatibility aliases
Header = HeaderGenerator
Documentation = DocumentationGenerator
Testbench = TestbenchGenerator

__all__ = [
    # Core domain classes
    "Module",
    "Bus",
    "Register",
    "Field",
    "RegisterMode",
    "RegisterType",
    "FieldType",
    # Generator classes
    "HeaderGenerator",
    "DocumentationGenerator",
    "TestbenchGenerator",
    "GeneratorFactory",
    # Backward compatibility
    "Header",
    "Documentation",
    "Testbench",
]
