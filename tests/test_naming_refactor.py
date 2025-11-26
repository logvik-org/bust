"""
Test suite to verify PEP 8 naming refactoring and backward compatibility.

This test ensures that:
1. New PEP 8 compliant methods work correctly
2. Old method names still work (backward compatibility)
3. Both produce identical output
"""

import unittest
import logging.config
from bust.utils import json_parser
from bust.module import Module
from bust.bus import Bus
from bust.settings import Settings
from bust.testbench import Testbench
from bust.documentation import Documentation
from bust.header import Header


class TestNamingRefactor(unittest.TestCase):
    """Test backward compatibility and new naming conventions."""

    def setUp(self):
        """Set up test fixtures."""
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
            level=logging.DEBUG,
        )
        self.logger = logging.getLogger(__name__)

        # Load test data
        json_file = "example/example_axi.json"
        json = json_parser(json_file)
        self.sett = Settings(json_file, json["settings"])
        self.bus = Bus(json["bus"])
        self.mod = Module(json["module"], self.bus, self.sett)
        self.tb = Testbench(self.mod, self.bus.create_vhdl_generator(), self.sett)
        self.doc = Documentation(self.mod)
        self.hdr = Header(self.mod)

    def test_module_methods(self):
        """Test Module class method naming."""
        # Test JSON conversion
        old_json = self.mod.return_JSON()
        new_json = self.mod.to_json()
        self.assertEqual(
            old_json,
            new_json,
            "return_JSON and to_json should produce identical output",
        )

        # Test VHDL generation
        old_vhdl = self.mod.return_module_VHDL()
        new_vhdl = self.mod.generate_module_vhdl()
        self.assertEqual(
            old_vhdl,
            new_vhdl,
            "return_module_VHDL and generate_module_vhdl should produce identical output",
        )

        # Test package generation
        old_pkg = self.mod.return_module_pkg_VHDL()
        new_pkg = self.mod.generate_module_package_vhdl()
        self.assertEqual(
            old_pkg,
            new_pkg,
            "return_module_pkg_VHDL and generate_module_package_vhdl should produce identical output",
        )

    def test_bus_methods(self):
        """Test Bus class method naming."""
        # Test JSON conversion
        old_json = self.bus.return_JSON()
        new_json = self.bus.to_json()
        self.assertEqual(
            old_json,
            new_json,
            "return_JSON and to_json should produce identical output",
        )

        # Test VHDL generator creation
        old_gen = self.bus.get_VHDL_generator()
        new_gen = self.bus.create_vhdl_generator()
        self.assertEqual(
            type(old_gen),
            type(new_gen),
            "get_VHDL_generator and create_vhdl_generator should return same type",
        )

        # Test bus package generation
        old_pkg = self.bus.return_bus_pkg_VHDL()
        new_pkg = self.bus.generate_bus_package_vhdl()
        self.assertEqual(
            old_pkg,
            new_pkg,
            "return_bus_pkg_VHDL and generate_bus_package_vhdl should produce identical output",
        )

        # Test PIF generation
        old_pif = self.bus.return_bus_pif_VHDL(self.mod)
        new_pif = self.bus.generate_bus_pif_vhdl(self.mod)
        self.assertEqual(
            old_pif,
            new_pif,
            "return_bus_pif_VHDL and generate_bus_pif_vhdl should produce identical output",
        )

    def test_settings_methods(self):
        """Test Settings class method naming."""
        # Test JSON conversion
        old_json = self.sett.return_JSON()
        new_json = self.sett.to_json()
        self.assertEqual(
            old_json,
            new_json,
            "return_JSON and to_json should produce identical output",
        )

    def test_header_methods(self):
        """Test Header class method naming."""
        # Test C header
        old_c = self.hdr.return_c_header()
        new_c = self.hdr.generate_c_header()
        self.assertEqual(
            old_c,
            new_c,
            "return_c_header and generate_c_header should produce identical output",
        )

        # Test C++ header
        old_cpp = self.hdr.return_cpp_header()
        new_cpp = self.hdr.generate_cpp_header()
        self.assertEqual(
            old_cpp,
            new_cpp,
            "return_cpp_header and generate_cpp_header should produce identical output",
        )

        # Test Python header
        old_py = self.hdr.return_python_header()
        new_py = self.hdr.generate_python_header()
        self.assertEqual(
            old_py,
            new_py,
            "return_python_header and generate_python_header should produce identical output",
        )

    def test_testbench_methods(self):
        """Test Testbench class method naming."""
        # Test UVVM component list
        old_comp = self.tb.return_uvvm_component_list()
        new_comp = self.tb.generate_uvvm_component_list()
        self.assertEqual(
            old_comp,
            new_comp,
            "return_uvvm_component_list and generate_uvvm_component_list should produce identical output",
        )

        # Test TCL script
        old_tcl = self.tb.return_tcl_script()
        new_tcl = self.tb.generate_tcl_script()
        self.assertEqual(
            old_tcl,
            new_tcl,
            "return_tcl_script and generate_tcl_script should produce identical output",
        )

        # Test VHDL testbench
        old_tb = self.tb.return_vhdl_tb()
        new_tb = self.tb.generate_vhdl_testbench()
        self.assertEqual(
            old_tb,
            new_tb,
            "return_vhdl_tb and generate_vhdl_testbench should produce identical output",
        )

    def test_documentation_methods(self):
        """Test Documentation class method naming."""
        # Test LaTeX documentation
        old_tex = self.doc.return_tex_documentation()
        new_tex = self.doc.generate_tex_documentation()
        self.assertEqual(
            old_tex,
            new_tex,
            "return_tex_documentation and generate_tex_documentation should produce identical output",
        )

    def test_register_properties(self):
        """Test Register class property conversion."""
        # Test mode_string property
        for reg in self.mod.registers:
            old_mode = reg.get_mode()
            new_mode = reg.mode_string
            self.assertEqual(
                old_mode,
                new_mode,
                "get_mode() and mode_string should return identical values",
            )

    def test_module_properties(self):
        """Test Module class property conversion."""
        # Note: get_next_address() has side effects (appends to addresses list),
        # so it was kept as a method rather than converted to a property.
        # This is aligned with Python best practices where properties should not have side effects.
        pass

    def test_class_aliases(self):
        """Test that class aliases work for backward compatibility."""
        from bust.module_vhdl_gen import ModuleVHDLGen, ModuleVhdlGenerator
        from bust.bus_vhdl_gen import BusVHDLGen, BusVhdlGenerator

        # Test that aliases point to the same class
        self.assertIs(
            ModuleVHDLGen,
            ModuleVhdlGenerator,
            "ModuleVHDLGen should be an alias for ModuleVhdlGenerator",
        )
        self.assertIs(
            BusVHDLGen,
            BusVhdlGenerator,
            "BusVHDLGen should be an alias for BusVhdlGenerator",
        )


if __name__ == "__main__":
    unittest.main()
