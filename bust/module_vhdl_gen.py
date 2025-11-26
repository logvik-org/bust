from bust.jinja_utils.environment import render_template


class ModuleVhdlGenerator:
    """VHDL code generator for Module."""

    def __init__(self, name, bus_gen, regs, data_width, addr_width):
        """Code generator for the Module module."""
        self.name = name
        self.bus = bus_gen
        self.registers = regs
        self.data_width = data_width
        self.addr_width = addr_width

    def generate_module_package_vhdl(self, module) -> str:
        """Generate VHDL package for the module."""
        return render_template(
            "vhdl/module/pif/pkg.j2",
            {
                "module": module,
                "addr_width": self.addr_width,
                "data_width": self.data_width,
            },
        )

    def generate_module_vhdl(self, module) -> str:
        """Generate VHDL module code."""
        return render_template(
            "vhdl/module/module.j2",
            {
                "module": module,
                "bus": self.bus,
            },
        )


# Backward compatibility alias
ModuleVHDLGen = ModuleVhdlGenerator
