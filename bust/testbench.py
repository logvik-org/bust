"""Testbench generation module for bust.

This module provides the Testbench class for generating VHDL testbenches
and TCL simulation scripts for ModelSim/QuestaSim. It supports UVVM-based
testbenches for AXI and IPBus modules.
"""

import logging
from bust.jinja_utils.environment import get_environment


class Testbench(object):
    """Generates VHDL testbenches and simulation scripts.

    The Testbench class creates UVVM-based VHDL testbenches and TCL scripts
    for ModelSim/QuestaSim simulation. It handles dependencies and paths for
    UVVM components and bus-specific VIPs.

    Attributes:
        module: Module instance to generate testbench for.
        bus: Bus configuration for the module.
        settings: Project settings with paths to UVVM and VIP libraries.
    """

    def __init__(self, module, bus, settings):
        """Initialize Testbench generator.

        Args:
            module: Module instance to create testbench for.
            bus: Bus configuration instance.
            settings: Settings instance with library paths.
        """
        self.logger = logging.getLogger(__name__)
        self.module = module
        self.bus = bus
        self.settings = settings

    @staticmethod
    def get_addr_func():
        """Generate VHDL address calculation function.

        Returns:
            VHDL function definition for f_addr that adds base and register
            addresses.
        """
        s = (
            "function f_addr (\n"
            "  BASE : std_logic_vector(31 downto 0);\n"
            "  REG  : std_logic_vector(31 downto 0))\n"
            "  return unsigned is\n"
            "  variable tmp : unsigned(31 downto 0);\n"
            "begin  -- function f_addr\n"
            "  tmp := unsigned(BASE);\n"
            "  tmp := tmp + unsigned(REG);\n"
            "  return tmp;\n"
            "end function f_addr;\n"
        )
        return s

    def return_uvvm_component_list(self):
        """Generate list of required UVVM components.

        Returns:
            Newline-separated string of UVVM component names needed for
            compilation, including bus-specific VIPs.
        """
        self.logger.debug("Generating UVVM Component List")
        string = "uvvm_util\n"
        string += "uvvm_vvc_framework\n"
        string += "bitvis_vip_scoreboard"
        if self.bus.bus_type == "axi":
            string += "\nbitvis_vip_axilite"
        string += "\n"
        return string

    def return_tcl_script(self):
        """Generate TCL simulation script for ModelSim/QuestaSim.

        Returns:
            TCL script content for compiling and simulating the testbench.
        """
        self.logger.debug("Generating TCL Script")

        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the TCL script template
        template = env.get_template("tcl/simulate_script.j2")

        # Define context for template rendering
        context = {
            "module": self.module,
            "bus": self.bus,
            "settings": self.settings,
        }
        result = template.render(context)
        # Ensure final newline is preserved
        if not result.endswith("\n"):
            result += "\n"
        return result

    def return_vhdl_tb(self):
        """Generate VHDL testbench code.

        Returns:
            Complete VHDL testbench source code with UVVM integration.
        """
        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the testbench template
        template = env.get_template("vhdl/testbench/testbench.j2")

        # Define context for template rendering
        context = {
            "module": self.module,
            "bus": self.bus,
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return template.render(context)
