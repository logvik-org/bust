from bust.jinja_utils.environment import get_environment


class BusVhdlGenerator:
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
            # Get standardized Jinja2 environment with all filters
            env = get_environment()

            # Load the AXI bus package template
            template = env.get_template("vhdl/bus/axi_pkg.j2")

            # Define context for template rendering
            context = {
                "bus_type": self.bus_type,
                "data_width": self.data_width,
                "addr_width": self.addr_width,
            }
            result: str = template.render(context)
            # Ensure final newline is preserved
            if not result.endswith("\n"):
                result += "\n"
            return result

        raise NotImplementedError(
            f"Bus package generation not implemented for bus type '{self.bus_type}'. "
            f"Only 'axi' bus type is currently supported."
        )

    def return_bus_pkg_VHDL(self) -> str:
        """Deprecated: Use generate_bus_package_vhdl() instead."""
        return self.generate_bus_package_vhdl()

    def generate_bus_pif_vhdl(self, mod) -> str:
        """Generate VHDL PIF (Physical Interface) for the bus."""
        # Get standardized Jinja2 environment with all filters
        env = get_environment()

        # Load the IPBus-specific module template
        template = env.get_template("vhdl/module/pif/pif.j2")

        # Define context for template rendering
        context = {
            "module": mod,
            "bus": self,
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return str(template.render(context))

    def return_bus_pif_VHDL(self, mod) -> str:
        """Deprecated: Use generate_bus_pif_vhdl() instead."""
        return self.generate_bus_pif_vhdl(mod)


# Backward compatibility alias
BusVHDLGen = BusVhdlGenerator
