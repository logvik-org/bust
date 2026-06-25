"""Factory for creating VHDL generator instances.

This module provides a factory class for creating VHDL generator instances,
decoupling the domain classes (Module and Bus) from the generator implementations.
"""

from typing import TYPE_CHECKING

from bust.generators.vhdl.module_generator import ModuleGenerator

if TYPE_CHECKING:
    from bust.core.module import Module


class GeneratorFactory:
    """Factory for creating VHDL generator instances.

    This factory centralizes the creation of generator instances,
    removing the need for domain classes to know about generator
    implementation details.
    """

    @staticmethod
    def create_module_generator() -> ModuleGenerator:
        """Create the (stateless) local-bus VHDL generator.

        Returns:
            ModuleGenerator that renders a module's local-bus artifacts.
        """
        return ModuleGenerator()

    @staticmethod
    def generate_regfile_package_vhdl(module: "Module") -> str:
        """Generate the local-bus regfile package VHDL for a module.

        Args:
            module: Module instance to generate the regfile package for.

        Returns:
            VHDL package source with the storage/to_hw/from_hw record families,
            reset constant, and address-decode helpers.
        """
        generator = GeneratorFactory.create_module_generator()
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
        generator = GeneratorFactory.create_module_generator()
        return generator.generate_regfile_vhdl(module)

    @staticmethod
    def generate_axi_endpoint_vhdl(module: "Module") -> str:
        """Generate the AXI4-Lite endpoint wrapper VHDL for a module.

        Args:
            module: Module instance to generate the AXI endpoint for.

        Returns:
            VHDL entity/architecture bridging AXI4-Lite to the local bus regfile.
        """
        generator = GeneratorFactory.create_module_generator()
        return generator.generate_axi_endpoint_vhdl(module)

    @staticmethod
    def generate_ipb_endpoint_vhdl(module: "Module") -> str:
        """Generate the IPBus endpoint wrapper VHDL for a module.

        Args:
            module: Module instance to generate the IPBus endpoint for.

        Returns:
            VHDL entity/architecture bridging IPBus to the local bus regfile.
        """
        generator = GeneratorFactory.create_module_generator()
        return generator.generate_ipb_endpoint_vhdl(module)

    @staticmethod
    def generate_module_top_vhdl(module: "Module") -> str:
        """Generate the thin top-level wrapper VHDL for a module.

        Args:
            module: Module instance to generate the top-level wrapper for.

        Returns:
            VHDL entity/architecture instantiating the bus endpoint, exposing the
            protocol ports and the to_hw/from_hw records.
        """
        generator = GeneratorFactory.create_module_generator()
        return generator.generate_module_top_vhdl(module)

    @staticmethod
    def generate_localbus_axi_testbench_vhdl(module: "Module") -> str:
        """Generate the UVVM AXI testbench for a module's local-bus top wrapper.

        Args:
            module: Module instance to generate the testbench for.

        Returns:
            VHDL UVVM testbench that drives the top wrapper over the AXI-Lite VIP
            and self-checks the plain read-write registers.
        """
        generator = GeneratorFactory.create_module_generator()
        return generator.generate_localbus_axi_testbench_vhdl(module)

    @staticmethod
    def generate_localbus_ipbus_testbench_vhdl(module: "Module") -> str:
        """Generate the UVVM IPBus testbench for a module's local-bus top wrapper.

        Args:
            module: Module instance to generate the testbench for.

        Returns:
            VHDL UVVM testbench that drives the top wrapper over the vip_ipbus VIP
            and self-checks the register-map access modes.
        """
        generator = GeneratorFactory.create_module_generator()
        return generator.generate_localbus_ipbus_testbench_vhdl(module)
