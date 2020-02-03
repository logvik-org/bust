import unittest
import logging.config
from bust.utils import json_parser
import bust.module as mod
import bust.bus as bus
import bust.settings as sett
import bust.header as hdr


class TestHeader(unittest.TestCase):
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
        self.hdr = hdr.Header(self.mod)

    def test_axi_hdr(self):
        self.logger.info("Testing Header generation...")
        with open('example/example_axi/header/example_axi.h') as f:
            string = f.read()
        self.assertEqual(self.hdr.return_c_header(), string, "c header must match manual file")

        with open('example/example_axi/header/example_axi.hpp') as f:
            string = f.read()
        self.assertEqual(self.hdr.return_cpp_header(), string, "c++ header must match manual file")

        with open('example/example_axi/header/example_axi.py') as f:
            string = f.read()
        self.assertEqual(self.hdr.return_python_header(), string, "python header must match manual file")


if __name__ == '__main__':
    unittest.main()
