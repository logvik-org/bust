from bust.jinja_utils.environment import get_environment


class ModuleVHDLGen:
    def __init__(self, name, bus_gen, regs, data_width, addr_width):
        """Code generator for the Module module."""
        self.name = name
        self.bus = bus_gen
        self.registers = regs
        self.data_width = data_width
        self.addr_width = addr_width

    def return_module_pkg_VHDL(self, module) -> str:
        # Get standardized Jinja2 environment
        env = get_environment()

        # Load the template
        template = env.get_template("vhdl/module/pif/pkg.j2")

        # Define context for template rendering
        context = {
            "module": module,
            "addr_width": self.addr_width,
            "data_width": self.data_width,
        }

        return str(template.render(context))

    def return_module_VHDL(self, module) -> str:
        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the module template
        template = env.get_template("vhdl/module/module.j2")

        # Define context for template rendering
        context = {
            "module": module,
            "bus": self.bus,  # Assumes `module` has an attribute `bus`
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return str(template.render(context))
