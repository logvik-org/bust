"""VHDL code generator for Module.

Generates the local-bus artifacts for a module: the regfile package and entity,
the per-protocol bus endpoint, the thin top-level wrapper, and the UVVM
testbenches. Each method renders purely from the Module, so the generator holds
no state.
"""

import re

from bust.jinja_utils.environment import render_template


class ModuleGenerator:
    """VHDL code generator for Module."""

    def generate_localbus_package_vhdl(self, module) -> str:
        """Generate the protocol-agnostic local-bus interface support package."""
        return render_template("vhdl/module/localbus_pkg.j2", {"module": module})

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

    def generate_sbi_endpoint_vhdl(self, module) -> str:
        """Generate the SBI endpoint wrapper over the local-bus regfile."""
        return render_template("vhdl/module/sbi_endpoint.j2", {"module": module})

    def generate_avalon_endpoint_vhdl(self, module) -> str:
        """Generate the Avalon-MM endpoint wrapper over the local-bus regfile."""
        return render_template("vhdl/module/avalon_endpoint.j2", {"module": module})

    def generate_wishbone_endpoint_vhdl(self, module) -> str:
        """Generate the Wishbone endpoint wrapper over the local-bus regfile."""
        return render_template("vhdl/module/wishbone_endpoint.j2", {"module": module})

    def generate_module_top_vhdl(self, module) -> str:
        """Generate the thin top-level wrapper instantiating the bus endpoint."""
        return render_template(
            "vhdl/module/module_top.j2", {"module": module, "bus": module.bus}
        )

    def generate_localbus_axi_testbench_vhdl(self, module) -> str:
        """Generate the UVVM AXI testbench driving the module's top wrapper."""
        return render_template("vhdl/testbench/localbus_axi_tb.j2", {"module": module})

    def generate_localbus_ipbus_testbench_vhdl(self, module) -> str:
        """Generate the UVVM IPBus testbench driving the module's top wrapper."""
        return render_template(
            "vhdl/testbench/localbus_ipbus_tb.j2", {"module": module}
        )

    def generate_localbus_sbi_testbench_vhdl(self, module) -> str:
        """Generate the UVVM SBI testbench driving the module's top wrapper."""
        return render_template("vhdl/testbench/localbus_sbi_tb.j2", {"module": module})

    def generate_localbus_avalon_testbench_vhdl(self, module) -> str:
        """Generate the UVVM Avalon-MM testbench driving the module's top wrapper."""
        return render_template(
            "vhdl/testbench/localbus_avalon_tb.j2", {"module": module}
        )

    def generate_localbus_wishbone_testbench_vhdl(self, module) -> str:
        """Generate the Wishbone testbench (inlined master BFM) for the top wrapper."""
        return render_template(
            "vhdl/testbench/localbus_wishbone_tb.j2", {"module": module}
        )


# Backward compatibility aliases
ModuleVhdlGenerator = ModuleGenerator
ModuleVHDLGen = ModuleGenerator
