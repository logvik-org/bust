from jinja2 import Environment, FileSystemLoader
import os

from bust.utils import indent_string
from bust.vhdl_gen import comb_process_with_reset
from bust.vhdl_gen import (
    _seq_process_async_reset,
    comb_process,
    _seq_process_sync_reset,
    seq_process,
)
from bust.jinja_utils.filters import indent_all


class BusVHDLGen:
    def __init__(
        self,
        bus_type,
        comp_library,
        data_width,
        addr_width,
    ):
        """Code generator for the Bus module."""
        self.bus_type = bus_type
        self.comp_library = comp_library
        self.clk_name = "clk"
        self.data_width = data_width
        self.addr_width = addr_width

        if self.bus_type == "axi":
            self.short_name = "axi"
            self.in_type = "t_axi_mosi"
            self.out_type = "t_axi_miso"
            self.bus_reset = "async"
            self.reset_active_high = False
            self.reset_async = True

        elif self.bus_type == "ipbus":
            self.short_name = "ipb"
            self.in_type = "ipb_wbus"
            self.out_type = "ipb_rbus"
            self.bus_reset = "sync"
            self.reset_active_high = True
            self.reset_async = False

        if self.reset_active_high:
            if self.bus_reset == "async":
                self.reset_name = "areset  "
            else:
                self.reset_name = "reset   "
        else:
            if self.bus_reset == "async":
                self.reset_name = "areset_n"
            else:
                self.reset_name = "reset_n "

    def return_bus_pkg_VHDL(self):
        if self.bus_type == "axi":

            s = "library ieee;\n"
            s += "use ieee.std_logic_1164.all;\n"
            s += "\n"

            s += "package " + self.bus_type + "_pkg is\n"
            s += "\n\n"

            data_width_constant = "C_" + self.bus_type.upper() + "_DATA_WIDTH"
            addr_width_constant = "C_" + self.bus_type.upper() + "_ADDR_WIDTH"
            data_sub_type = "t_" + self.bus_type + "_data"
            addr_sub_type = "t_" + self.bus_type + "_addr"

            par = ""
            par += "constant " + data_width_constant
            par += " : natural := " + str(self.data_width) + ";\n"
            par += "constant " + addr_width_constant
            par += " : natural := " + str(self.addr_width) + ";\n"
            par += "\n"
            par += "subtype " + data_sub_type + " is std_logic_vector("
            par += data_width_constant + "-1 downto 0);\n"
            par += "subtype " + addr_sub_type + " is std_logic_vector("
            par += addr_width_constant + "-1 downto 0);\n"
            par += "\n"
            s += indent_string(par)

            s += indent_string("type t_" + self.bus_type)
            s += "_mosi is record\n"
            par = ""
            par += "araddr  : " + addr_sub_type + ";\n"
            par += "arvalid : std_logic;\n"
            par += "awaddr  : " + addr_sub_type + ";\n"
            par += "awvalid : std_logic;\n"
            par += "bready  : std_logic;\n"
            par += "rready  : std_logic;\n"
            par += "wdata   : " + data_sub_type + ";\n"
            par += "wvalid  : std_logic;\n"
            s += indent_string(par, 2)
            s += indent_string("end record;\n")
            s += "\n"

            s += indent_string("type t_" + self.bus_type)
            s += "_miso is record\n"
            par = ""
            par += "arready : std_logic;\n"
            par += "awready : std_logic;\n"
            par += "bresp   : std_logic_vector(1 downto 0);\n"
            par += "bvalid  : std_logic;\n"
            par += "rdata   : " + data_sub_type + ";\n"
            par += "rresp   : std_logic_vector(1 downto 0);\n"
            par += "rvalid  : std_logic;\n"
            par += "wready  : std_logic;\n"
            s += indent_string(par, 2)
            s += indent_string("end record;\n")
            s += "\n"

            s += "end " + self.bus_type + "_pkg;"
            s += "\n"

        return s

    def return_bus_pif_VHDL(self, mod):
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")

        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        env.filters["indent_all"] = indent_all

        # Load the IPBus-specific module template
        template = env.get_template("vhdl/module/pif/pif.j2")

        # Define context for template rendering
        context = {
            "module": mod,
            "bus": mod.bus,  # Assumes `module` has an attribute `bus`
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return template.render(context)
