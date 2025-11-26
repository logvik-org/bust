"""VHDL code generator for Bus.

This module provides the BusGenerator class for generating VHDL bus interface
code and package definitions.
"""

from bust.jinja_utils.environment import render_template


class BusGenerator:
    """VHDL code generator for Bus."""

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
                self.reset_name = "areset"
            else:
                self.reset_name = "reset"
        else:
            if self.bus_reset == "async":
                self.reset_name = "areset_n"
            else:
                self.reset_name = "reset_n"

    def generate_bus_package_vhdl(self) -> str:
        """Generate VHDL package for the bus."""
        if self.bus_type == "axi":
            return render_template(
                "vhdl/bus/axi_pkg.j2",
                {
                    "bus_type": self.bus_type,
                    "data_width": self.data_width,
                    "addr_width": self.addr_width,
                },
            )

        raise NotImplementedError(
            f"Bus package generation not implemented for bus type '{self.bus_type}'. "
            f"Only 'axi' bus type is currently supported."
        )

    def generate_bus_pif_vhdl(self, mod) -> str:
        """Generate VHDL PIF (Physical Interface) for the bus."""
        return render_template(
            "vhdl/module/pif/pif.j2",
            {
                "module": mod,
                "bus": self,
            },
        )


# Backward compatibility aliases
BusVhdlGenerator = BusGenerator
BusVHDLGen = BusGenerator
