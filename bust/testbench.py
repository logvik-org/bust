import logging
from bust.jinja_utils.environment import get_environment


class Testbench:
    """Class for generating testbenches and tcl scripts for Model/Questa Sim"""

    def __init__(self, module, bus, settings):
        self.logger = logging.getLogger(__name__)
        self.module = module
        self.bus = bus
        self.settings = settings

    def return_uvvm_component_list(self):
        self.logger.debug("Generating UVVM Component List")

        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the component list template
        template = env.get_template("uvvm/component_list.j2")

        # Define context for template rendering
        context = {
            "bus": self.bus,
        }
        result = template.render(context)
        # Ensure final newline is preserved
        if not result.endswith("\n"):
            result += "\n"
        return result

    def return_tcl_script(self):
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
