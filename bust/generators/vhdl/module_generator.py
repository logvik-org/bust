"""VHDL code generator for Module.

This module provides the ModuleGenerator class for generating VHDL module
code and package definitions from Module instances.
"""

import re

from bust.jinja_utils.environment import render_template


class ModuleGenerator:
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

    def generate_regfile_package_vhdl(self, module) -> str:
        """Generate the local-bus regfile package (record families + decode helpers)."""
        return render_template("vhdl/module/regfile_pkg.j2", {"module": module})

    def generate_regfile_vhdl(self, module) -> str:
        """Generate the local-bus regfile entity (storage, side effects, read mux)."""
        out = render_template("vhdl/module/regfile.j2", {"module": module})
        # Per-register write blocks render with variable spacing; collapse runs of
        # blank lines so consecutive blocks are separated by exactly one.
        return re.sub(r"\n{3,}", "\n\n", out)

    def generate_axi_endpoint_vhdl(self, module) -> str:
        """Generate the AXI4-Lite endpoint wrapper over the local-bus regfile."""
        return render_template("vhdl/module/axi_endpoint.j2", {"module": module})

    def generate_ipb_endpoint_vhdl(self, module) -> str:
        """Generate the IPBus endpoint wrapper over the local-bus regfile."""
        return render_template("vhdl/module/ipb_endpoint.j2", {"module": module})

    def generate_module_top_vhdl(self, module) -> str:
        """Generate the thin top-level wrapper instantiating the bus endpoint."""
        return render_template(
            "vhdl/module/module_top.j2", {"module": module, "bus": module.bus}
        )

    def generate_localbus_axi_testbench_vhdl(self, module) -> str:
        """Generate the UVVM AXI testbench driving the module's top wrapper."""
        return render_template("vhdl/testbench/localbus_axi_tb.j2", {"module": module})

    def generate_module_vhdl(self, module) -> str:
        """Generate VHDL module code."""
        return render_template(
            "vhdl/module/module.j2",
            {
                "module": module,
                "bus": self.bus,
            },
        )


# Backward compatibility aliases
ModuleVhdlGenerator = ModuleGenerator
ModuleVHDLGen = ModuleGenerator
