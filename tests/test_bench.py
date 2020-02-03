import unittest
import logging.config
from bust.utils import json_parser
import bust.module as mod
import bust.bus as bus
import bust.settings as sett
import bust.testbench as tb

class TestBench(unittest.TestCase):
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
        self.tb = tb.Testbench(self.mod, self.bus, self.sett)

    def test_axi_scripts(self):
        self.logger.info("Testing TB Script generation...")
        with open('example/example_axi/scripts/simulate_axi_pif.do') as f:
            string = f.read()
        self.assertEqual(self.tb.return_tcl_script(), string, ".tcl script must match manual file")

        with open('example/example_axi/scripts/component_list.txt') as f:
            string = f.read()
        self.assertEqual(self.tb.return_uvvm_component_list(), string, ".txt file must match manual file")

    def test_axi_tb(self):
        self.logger.info("Testing TB Sequencer generation...")
        with open('example/example_axi/tb/example_axi_axi_pif_tb.vhd') as f:
            string = f.read()
        self.assertEqual(self.tb.return_vhdl_tb(), string, ".vhd TB must match manual file")

if __name__ == '__main__':
    unittest.main()