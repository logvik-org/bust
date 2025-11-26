"""Testbench generation module for bust.

This module provides the TestbenchGenerator class for generating VHDL testbenches
and TCL simulation scripts for ModelSim/QuestaSim. It supports UVVM-based
testbenches for AXI and IPBus modules.
"""

import logging
from bust.jinja_utils.environment import render_template


class TestbenchGenerator:
    """Generates VHDL testbenches and simulation scripts.

    The TestbenchGenerator class creates UVVM-based VHDL testbenches and TCL scripts
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

    def generate_uvvm_component_list(self):
        """Generate list of required UVVM components.

        Returns:
            Newline-separated string of UVVM component names needed for
            compilation, including bus-specific VIPs.
        """
        self.logger.debug("Generating UVVM Component List")
        return render_template("uvvm/component_list.j2", {"bus": self.bus})

    def generate_tcl_script(self):
        """Generate TCL simulation script for ModelSim/QuestaSim.

        Returns:
            TCL script content for compiling and simulating the testbench.
        """
        self.logger.debug("Generating TCL Script")
        return render_template(
            "tcl/simulate_script.j2",
            {
                "module": self.module,
                "bus": self.bus,
                "settings": self.settings,
            },
        )

    def generate_vhdl_testbench(self):
        """Generate VHDL testbench code.

        Returns:
            Complete VHDL testbench source code with UVVM integration.
        """
        return render_template(
            "vhdl/testbench/testbench.j2",
            {
                "module": self.module,
                "bus": self.bus,
            },
        )


# Backward compatibility alias
Testbench = TestbenchGenerator
