import logging
from jinja2 import Environment, FileSystemLoader
from bust.jinja_utils.filters import indent_all
import os
from bust.bus import Bus


class Testbench(object):
    """Class for generating testbenches and tcl scripts for Model/Questa Sim"""

    def __init__(self, module, bus, settings):
        self.logger = logging.getLogger(__name__)
        self.module = module
        self.bus = bus
        self.settings = settings

    @staticmethod
    def get_addr_func():
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
        self.logger.debug("Generating UVVM Component List")
        string = "uvvm_util\n"
        string += "uvvm_vvc_framework\n"
        string += "bitvis_vip_scoreboard"
        if self.bus.bus_type == "axi":
            string += "\nbitvis_vip_axilite"
        string += "\n"
        return string

    def return_tcl_script(self):
        self.logger.debug("Generating TCL Script")

        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        env.filters["indent_all"] = indent_all

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

        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")

        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        env.filters["indent_all"] = indent_all

        # Load the IPBus-specific module template
        template = env.get_template("vhdl/testbench/testbench.j2")

        # Define context for template rendering
        context = {
            "module": self.module,
            "bus": self.bus,
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return template.render(context)
