import unittest
import logging.config
from bust.utils import json_parser
import bust.module as mod
import bust.bus as bus
import bust.settings as sett
import bust.documentation as doc


class TestDocumentation(unittest.TestCase):
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
        self.doc = doc.Documentation(self.mod)

    def test_axi_doc(self):
        self.logger.info("Testing Doc generation...")
        with open('example/example_axi/doc/example_axi.tex') as f:
            string = f.read()
        self.assertEqual(self.doc.return_tex_documentation(), string, "doc must match manual file")


if __name__ == '__main__':
    unittest.main()
