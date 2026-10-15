"""bust - a register-map generator for VHDL.

bust reads a JSON register map and generates a VHDL register file with a bus
endpoint, a self-checking UVVM testbench, C/C++/Python headers, an IPBus
address table and LaTeX documentation. Supported buses: AXI4-Lite, IPBus, SBI,
Avalon-MM, Wishbone and APB.

Package structure:
    - core: Domain models (Module, Bus, Register, Field, Enums)
    - generators: Code generation (VHDL, headers, documentation, testbenches)
    - validation: VHDL identifier and configuration validation
    - utils: File I/O, JSON parsing, and string formatting utilities
    - jinja_utils: Jinja2 template utilities
"""

from bust.core import (
    Module,
    Bus,
    Register,
    Field,
    RegisterMode,
    RegisterType,
    FieldType,
)
from bust.generators import (
    HeaderGenerator,
    DocumentationGenerator,
    GeneratorFactory,
)

__all__ = [
    "Module",
    "Bus",
    "Register",
    "Field",
    "RegisterMode",
    "RegisterType",
    "FieldType",
    "HeaderGenerator",
    "DocumentationGenerator",
    "GeneratorFactory",
]
