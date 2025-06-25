from jinja2 import Environment, FileSystemLoader
import os

from bust.utils import NL, indent_string


# Helper function to determine VHDL type
def get_vhdl_type(reg, module_name):
    """Returns the correct VHDL type based on the register's type."""
    if reg.sig_type == "default" or (reg.sig_type == "slv" and reg.width == 32):
        return f"t_{module_name}_data"
    elif reg.sig_type == "slv":
        return f"std_logic_vector({reg.width - 1} downto 0)"
    elif reg.sig_type == "sl":
        return "std_logic"
    elif reg.sig_type == "fields":
        return f"t_{module_name}_{reg.mode}_{reg.name}"
    else:
        raise RuntimeError(f"Unknown signal type: {reg.sig_type}")


# Helper function to format reset values
def get_reset_value(reg):
    """Returns the formatted VHDL reset value."""
    if reg.sig_type in ["default", "slv"]:
        return (
            "(others => '0')"
            if reg.reset == "0x0"
            else f'{reg.width}X"{int(reg.reset, 16):X}"'
        )
    elif reg.sig_type == "fields":
        return f"({', '.join([f'{field.name} => {field.get_reset_vhdl()}' for field in reg.fields])})"
    elif reg.sig_type == "sl":
        return f"'{int(reg.reset, 16):X}'"
    else:
        raise RuntimeError(f"Unknown reset type: {reg.sig_type}")


class ModuleVHDLGen:
    def __init__(self, name, bus_gen, regs, data_width, addr_width):
        """Code generator for the Module module."""
        self.name = name
        self.bus = bus_gen
        self.registers = regs
        self.data_width = data_width
        self.addr_width = addr_width
        self.n_rw_regs = len([reg for reg in self.registers if reg.mode == "rw"])
        self.n_ro_regs = len([reg for reg in self.registers if reg.mode == "ro"])
        self.n_pulse_regs = len([reg for reg in self.registers if reg.mode == "pulse"])

    def return_module_pkg_VHDL(self):

        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Register custom filters
        env.filters["get_vhdl_type"] = get_vhdl_type
        env.filters["get_reset_value"] = get_reset_value

        # Load the template
        template = env.get_template("vhdl/module/pif_pkg.j2")

        # Define context for template rendering
        context = {
            "module": self,
            "addr_width": self.addr_width,
            "data_width": self.data_width,
        }

        return template.render(context)

    def return_module_VHDL(self):
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Load the IPBus-specific module template
        template = env.get_template("vhdl/module/module.j2")

        # Define context for template rendering
        context = {
            "module": self,
            "bus": self.bus,  # Assumes `module` has an attribute `bus`
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return template.render(context)

    def get_instantiation(self, instance_name, intern_out=True):
        s = instance_name + " "
        s += ": entity work." + self.name + "_" + self.bus.short_name + "_pif\n"
        s += indent_string("generic map (\n")
        par = "g_{0}_baseaddr      => g_{0}_baseaddr,\n".format(self.bus.short_name)
        par += "g_check_baseaddr    => g_check_baseaddr,\n"
        par += "g_module_addr_width => g_module_addr_width)\n"
        s += indent_string(par, 2)

        s += indent_string("port map (\n")
        if intern_out:
            inter = "_i"
        else:
            inter = ""

        par = ""
        if self.n_rw_regs > 0:
            par += (
                self.bus.short_name
                + "_rw_regs         => "
                + self.bus.short_name
                + "_rw_regs,\n"
            )
        if self.n_ro_regs > 0:
            par += (
                self.bus.short_name
                + "_ro_regs         => "
                + self.bus.short_name
                + "_ro_regs,\n"
            )
        if self.n_pulse_regs > 0:
            par += (
                self.bus.short_name
                + "_pulse_regs      => "
                + self.bus.short_name
                + "_pulse_regs,\n"
            )

        par += (
            self.bus.clk_name
            + "                 => "
            + self.bus.short_name
            + "_"
            + self.bus.clk_name
            + ",\n"
        )
        par += (
            self.bus.reset_name
            + "            => "
            + self.bus.short_name
            + "_"
            + str.strip(self.bus.reset_name)
            + ",\n"
        )
        par += self.bus.get_instantiation(self.name, inter)

        par += ");\n"

        s += indent_string(par, 2)
        return s
