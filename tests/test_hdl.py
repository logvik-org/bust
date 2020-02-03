import unittest
import logging.config
from bust.utils import json_parser
import bust.module as mod
import bust.bus as bus
import bust.settings as sett
import bust.testbench as tb


class TestHDL(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s: %(message)s', level=logging.DEBUG)
        self.logger = logging.getLogger(__name__)

        # Load the example JSON file
        json_file = "example/example_axi.json"
        json = json_parser(json_file)
        self.sett = sett.Settings(json_file, json['settings'])
        self.bus = bus.Bus(json['bus'])
        self.mod = mod.Module(json['module'], self.bus, self.sett)

    def test_axi_pif(self):
        self.logger.info("Testing PIF generation...")
        with open('example/example_axi/hdl/example_axi_pif_pkg.vhd') as f:
            string = f.read()
        self.assertEqual(self.mod.return_module_pkg_VHDL(), string, "pif pkg must match manual file")

        with open('example/example_axi/hdl/example_axi_axi_pif.vhd') as f:
            string = f.read()
        self.assertEqual(self.bus.return_bus_pif_VHDL(self.mod), string, "axi pif must match manual file")

    def test_axi_module(self):
        self.logger.info("Testing Module generation...")
        with open('example/example_axi/hdl/example_axi.vhd') as f:
            string = f.read()
        self.assertEqual(self.mod.return_module_VHDL(), string, "module must match manual file")

    def test_axi_buspkg(self):
        self.logger.info("Testing Bus PKG generation...")
        with open('example/example_axi/hdl/axi_pkg.vhd') as f:
            string = f.read()
        self.assertEqual(self.bus.return_bus_pkg_VHDL(), string, "bus pkg must match manual file")


if __name__ == '__main__':
    unittest.main()
