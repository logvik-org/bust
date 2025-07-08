import logging
from jinja2 import Environment, FileSystemLoader
from bust.jinja_utils.filters import indent_all
import os
from bust.enums import FieldType, RegisterMode, RegisterType
from bust.utils import indent_string
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
        s = (
            "# Set default error behaviour\n"
            "if {[batch_mode]} {\n"
            "  onerror {abort all; exit -f -code 1}\n"
            "} else {\n"
            "  onerror {abort all}\n"
            "}\n\n"
            "# Shut down running simulation\n"
            "quit -sim\n\n"
            "# Set project paths\n"
        )

        s += 'set {}_path "../"\n'.format(self.module.name)

        s += 'set bus_path "{}"\n'.format(
            self.settings.return_sim_bus_path(self.bus.bus_type)
        )
        s += 'set UVVM_path "{}"\n'.format(self.settings.return_sim_uvvm_path())

        if self.bus.bus_type == "ipbus":
            s += 'set vip_ipbus_path "{}"\n'.format(
                self.settings.return_vip_ipbus_path()
            )

        s += (
            "\n# Compile UVVM Dependencies\n"
            "do $UVVM_path/script/compile_all.do $UVVM_path/script ${0}_path/{1} ${0}_path/"
            "{2}/component_list.txt\n\n".format(
                self.module.name, self.settings.sim_dir, self.settings.script_dir
            )
        )

        s += "# Set vcom args\n" 'set vcom_args "-quiet'
        if self.settings.coverage:
            s += " +cover=sbt"
        s += '"\n\n'

        if (
            self.bus.comp_library != Bus.default_comp_library
            or self.bus.bus_type == "ipbus"
        ):
            s += (
                "###########################################################################\n"
                "# Compile bus source files into library\n"
                "###########################################################################\n\n"
                "# Set up library and sim path\n"
                'set lib_name "'
            )
            s += self.bus.comp_library
            s += '"\n'
            if self.bus.bus_type == "ipbus":
                s += 'set bus_sim_path "${}_path/{}"\n\n'.format(
                    self.module.name, self.settings.sim_dir
                )
            else:
                s += 'set bus_sim_path "$bus_path/{}"\n\n'.format(self.settings.sim_dir)
            s += (
                "# (Re-)Generate library and Compile source files\n"
                'echo "\\nRe-gen lib and compile $lib_name source\\n"\n'
                "if {{[file exists $bus_sim_path/$lib_name]}} {{\n"
                "  file delete -force $bus_sim_path/$lib_name\n"
                "}}\n\n"
            ).format()

            s += "vlib $bus_sim_path/$lib_name\n"
            s += "vmap $lib_name $bus_sim_path/$lib_name\n\n"

            s += 'set vhdldirectives "-2008 -work $lib_name"\n\n'
            if self.bus.bus_type == "ipbus":
                s += "eval vcom $vcom_args $vhdldirectives $bus_path/components/ipbus_core/firmware/hdl/ipbus_package.vhd\n\n"
                s += "# Compile vip_ipbus Dependencies\n"
                s += "do $vip_ipbus_path/scripts/compile_src.do $vip_ipbus_path $vip_ipbus_path/sim\n"
            else:
                s += "eval vcom $vcom_args $vhdldirectives $bus_path/hdl/{}_pkg.vhd\n".format(
                    self.bus.bus_type
                )

        s += (
            "\n\n###########################################################################\n"
            "# Compile source files into library\n"
            "###########################################################################\n\n"
            "# Set up library and sim path\n"
            'set lib_name "'
        )
        s += self.module.name
        s += '"\n'
        s += 'set {0}_sim_path "${0}_path/{1}"\n\n'.format(
            self.module.name, self.settings.sim_dir
        )

        s += (
            "# (Re-)Generate library and Compile source files\n"
            'echo "\\nRe-gen lib and compile $lib_name source\\n"\n'
            "if {{[file exists ${0}_sim_path/$lib_name]}} {{\n"
            "  file delete -force ${0}_sim_path/$lib_name\n"
            "}}\n\n".format(self.module.name)
        )

        s += "vlib ${}_sim_path/$lib_name\n".format(self.module.name)
        s += "vmap $lib_name ${}_sim_path/$lib_name\n\n".format(self.module.name)

        s += 'set vhdldirectives "-2008 -work $lib_name"\n\n'

        if self.bus.comp_library == Bus.default_comp_library:
            s += "eval vcom $vcom_args $vhdldirectives $bus_path/hdl/{}_pkg.vhd\n".format(
                self.bus.bus_type
            )
        s += (
            "eval vcom $vcom_args $vhdldirectives ${0}_path/hdl/{0}_pif_pkg.vhd\n"
            "eval vcom $vcom_args $vhdldirectives ${0}_path/hdl/{0}_{1}_pif.vhd\n\n"
        ).format(self.module.name, self.bus.short_name)

        s += (
            "###########################################################################\n"
            "# Compile testbench files into library\n"
            "###########################################################################\n"
            'set vcom_args "-quiet"\n'
        )
        s += "eval vcom $vcom_args $vhdldirectives ${0}_path/tb/{0}_{1}_pif_tb.vhd\n\n".format(
            self.module.name, self.bus.short_name
        )

        s += (
            "###########################################################################\n"
            "# Simulate\n"
            "###########################################################################\n"
        )
        s += "vsim -quiet "
        if self.settings.coverage:
            s += "-coverage "
        s += "{0}.{0}_{1}_pif_tb\n\n".format(self.module.name, self.bus.short_name)

        s += (
            "# Trick to avoid metastability warnings\n"
            "set NumericStdNoWarnings 1\n"
            "run 1 ns;\n"
            "set NumericStdNoWarnings 0\n"
            "run -all\n\n"
        )

        if self.settings.coverage:
            if self.bus.bus_type == "axi":
                s += (
                    "coverage exclude -du {0}_{1}_pif -togglenode araddr\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode araddr_i\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode awaddr\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode awaddr_i\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode bresp\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode bresp_i\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode rresp\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode rresp_i\n"
                ).format(self.module.name, self.bus.short_name)
            s += "coverage report\n"
            s += "coverage report -html -htmldir covhtmlreport -code bcefst"

        s += "\n"

        return s

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
            "bus": self.module.bus,
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return template.render(context)
