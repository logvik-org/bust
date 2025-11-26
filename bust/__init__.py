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
"""
