import logging
from bust.jinja_utils.environment import render_template


class Testbench:
    """Class for generating testbenches and tcl scripts for Model/Questa Sim"""

    def __init__(self, module, bus, settings):
        self.logger = logging.getLogger(__name__)
        self.module = module
        self.bus = bus
        self.settings = settings

    def return_uvvm_component_list(self):
        self.logger.debug("Generating UVVM Component List")
        return render_template("uvvm/component_list.j2", {"bus": self.bus})

    def return_tcl_script(self):
        self.logger.debug("Generating TCL Script")
        return render_template(
            "tcl/simulate_script.j2",
            {
                "module": self.module,
                "bus": self.bus,
                "settings": self.settings,
            },
        )

    def return_vhdl_tb(self):
        # Get standardized Jinja2 environment with all filters
        return render_template(
            "vhdl/testbench/testbench.j2",
            {
                "module": self.module,
                "bus": self.bus,
            },
        )
