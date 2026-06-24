"""Factory for creating VHDL generator instances.

This module provides a factory class for creating VHDL generator instances,
decoupling the domain classes (Module and Bus) from the generator implementations.
"""

from typing import TYPE_CHECKING

from bust.generators.vhdl.bus_generator import BusGenerator
from bust.generators.vhdl.module_generator import ModuleGenerator

if TYPE_CHECKING:
    from bust.core.bus import Bus
    from bust.core.module import Module


class GeneratorFactory:
    """Factory for creating VHDL generator instances.

    This factory centralizes the creation of generator instances,
    removing the need for domain classes to know about generator
    implementation details.
    """

    @staticmethod
    def create_bus_generator(bus: "Bus") -> BusGenerator:
        """Create a VHDL generator instance for a bus configuration.

        Args:
            bus: Bus instance with interface configuration.

        Returns:
            BusGenerator instance configured for the bus type.
        """
        return BusGenerator(
            bus_type=bus.bus_type,
            comp_library=bus.comp_library,
            data_width=bus.data_width,
            addr_width=bus.addr_width,
        )

    @staticmethod
    def create_module_generator(module: "Module") -> ModuleGenerator:
        """Create a VHDL generator instance for a module.

        Args:
            module: Module instance with register definitions.

        Returns:
            ModuleGenerator configured with module and bus settings.
        """
        bus_gen = GeneratorFactory.create_bus_generator(module.bus)
        return ModuleGenerator(
            name=module.name,
            bus_gen=bus_gen,
            regs=module.registers,
            data_width=module.data_width,
            addr_width=module.addr_width,
        )

    @staticmethod
    def generate_module_package_vhdl(module: "Module") -> str:
        """Generate VHDL package code for a module.

        Args:
            module: Module instance to generate package for.

        Returns:
            VHDL package source code with register type definitions.
        """
        generator = GeneratorFactory.create_module_generator(module)
        return generator.generate_module_package_vhdl(module)

    @staticmethod
    def generate_regfile_package_vhdl(module: "Module") -> str:
        """Generate the local-bus regfile package VHDL for a module.

        Args:
            module: Module instance to generate the regfile package for.

        Returns:
            VHDL package source with the storage/to_hw/from_hw record families,
            reset constant, and address-decode helpers.
        """
        generator = GeneratorFactory.create_module_generator(module)
        return generator.generate_regfile_package_vhdl(module)

    @staticmethod
    def generate_regfile_vhdl(module: "Module") -> str:
        """Generate the local-bus regfile entity VHDL for a module.

        Args:
            module: Module instance to generate the regfile entity for.

        Returns:
            VHDL entity/architecture implementing storage, software side effects,
            hardware updates, the read mux, and the bus response.
        """
        generator = GeneratorFactory.create_module_generator(module)
        return generator.generate_regfile_vhdl(module)

    @staticmethod
    def generate_axi_endpoint_vhdl(module: "Module") -> str:
        """Generate the AXI4-Lite endpoint wrapper VHDL for a module.

        Args:
            module: Module instance to generate the AXI endpoint for.

        Returns:
            VHDL entity/architecture bridging AXI4-Lite to the local bus regfile.
        """
        generator = GeneratorFactory.create_module_generator(module)
        return generator.generate_axi_endpoint_vhdl(module)

    @staticmethod
    def generate_ipb_endpoint_vhdl(module: "Module") -> str:
        """Generate the IPBus endpoint wrapper VHDL for a module.

        Args:
            module: Module instance to generate the IPBus endpoint for.

        Returns:
            VHDL entity/architecture bridging IPBus to the local bus regfile.
        """
        generator = GeneratorFactory.create_module_generator(module)
        return generator.generate_ipb_endpoint_vhdl(module)

    @staticmethod
    def generate_module_vhdl(module: "Module") -> str:
        """Generate main VHDL module entity and architecture.

        Args:
            module: Module instance to generate VHDL for.

        Returns:
            VHDL source code for the complete bus slave module.
        """
        generator = GeneratorFactory.create_module_generator(module)
        return generator.generate_module_vhdl(module)

    @staticmethod
    def generate_bus_package_vhdl(bus: "Bus") -> str:
        """Generate VHDL package code for a bus interface.

        Args:
            bus: Bus instance to generate package for.

        Returns:
            VHDL package source code as a string.
        """
        generator = GeneratorFactory.create_bus_generator(bus)
        return generator.generate_bus_package_vhdl()

    @staticmethod
    def generate_bus_pif_vhdl(bus: "Bus", module: "Module") -> str:
        """Generate bus protocol interface VHDL code for a module.

        Args:
            bus: Bus instance with interface configuration.
            module: Module instance to generate interface code for.

        Returns:
            VHDL source code for the bus protocol interface.
        """
        generator = GeneratorFactory.create_bus_generator(bus)
        return generator.generate_bus_pif_vhdl(module)
