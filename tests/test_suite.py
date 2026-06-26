import unittest
import logging.config
from bust.utils.json_utils import json_parser
from bust.core.module import Module
from bust.core.bus import Bus
from bust.settings import Settings
from bust.generators.documentation_generator import Documentation
from bust.generators.header_generator import Header
from bust.generators.factory import GeneratorFactory


class BusHolder:
    def __init__(self, bus_type):
        self.sett, self.bus, self.mod, self.doc, self.hdr = self.load_bus(bus_type)

    def get_type(self):
        return self.bus.bus_type

    @staticmethod
    def load_bus(bus_type):
        # Load the example JSON file
        json_file = "example/example_{}.json".format(bus_type)
        json = json_parser(json_file)
        sett = Settings(json_file, json["settings"])
        bus = Bus(json["bus"])
        mod = Module(json["module"], bus, sett)
        doc = Documentation(mod)
        hdr = Header(mod)
        return sett, bus, mod, doc, hdr

    def __repr__(self):
        return self.get_type()


def _load_prototype(bus_type):
    """Build the prototype module over the requested bus.

    The prototype JSON pins AXI; the IPBus variant reuses its bus config and only
    swaps the type, so both stay in lockstep with the JSON.
    """
    json = json_parser("example/example_prototype.json")
    bus = Bus(dict(json["bus"], type=bus_type))
    mod = Module(json["module"], bus, settings=None)
    return bus, mod, Documentation(mod), Header(mod)


class Test_Suite(unittest.TestCase):
    maxDiff = None

    def __init__(self, *args, **kwargs):
        super(Test_Suite, self).__init__(*args, **kwargs)
        self.buzz = [BusHolder(bus_type) for bus_type in ["axi", "ipbus"]]

    def setUp(self):
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s: %(message)s",
            level=logging.DEBUG,
        )
        self.logger = logging.getLogger(__name__)

    def _assert_matches(self, generated, path, label):
        with open(path) as f:
            self.assertEqual(generated, f.read(), label)

    ############## Local-bus HDL Testing ##################

    def test_localbus_hdl(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing local-bus HDL generation...")
                t = holder.bus.bus_type
                mod = holder.mod
                base = "example/example_{0}/hdl/example_{0}".format(t)
                self._assert_matches(
                    GeneratorFactory.generate_localbus_package_vhdl(mod),
                    "example/example_{0}/hdl/localbus_pkg.vhd".format(t),
                    "local-bus package must match manual file",
                )
                self._assert_matches(
                    GeneratorFactory.generate_regfile_package_vhdl(mod),
                    base + "_regfile_pkg.vhd",
                    "regfile package must match manual file",
                )
                self._assert_matches(
                    GeneratorFactory.generate_regfile_vhdl(mod),
                    base + "_regfile.vhd",
                    "regfile must match manual file",
                )
                if t == "axi":
                    endpoint = GeneratorFactory.generate_axi_endpoint_vhdl(mod)
                    endpoint_path = base + "_axi_endpoint.vhd"
                else:
                    endpoint = GeneratorFactory.generate_ipb_endpoint_vhdl(mod)
                    endpoint_path = base + "_ipb_endpoint.vhd"
                self._assert_matches(
                    endpoint, endpoint_path, "endpoint must match manual file"
                )
                self._assert_matches(
                    GeneratorFactory.generate_module_top_vhdl(mod),
                    base + ".vhd",
                    "top wrapper must match manual file",
                )

    ############## Local-bus Testbench Testing ##################

    def test_localbus_tb(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing local-bus testbench generation...")
                t = holder.bus.bus_type
                mod = holder.mod
                if t == "axi":
                    tb = GeneratorFactory.generate_localbus_axi_testbench_vhdl(mod)
                else:
                    tb = GeneratorFactory.generate_localbus_ipbus_testbench_vhdl(mod)
                self._assert_matches(
                    tb,
                    "example/example_{0}/tb/example_{0}_tb.vhd".format(t),
                    "testbench must match manual file",
                )

    ############## Header Testing ##################

    def test_hdr(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing Header generation...")
                base = "example/example_{0}/header/example_{0}".format(
                    holder.bus.bus_type
                )
                self._assert_matches(
                    holder.hdr.generate_c_header(),
                    base + ".h",
                    "c header must match manual file",
                )
                self._assert_matches(
                    holder.hdr.generate_cpp_header(),
                    base + ".hpp",
                    "cpp header must match manual file",
                )
                self._assert_matches(
                    holder.hdr.generate_python_header(),
                    base + ".py",
                    "python header must match manual file",
                )
                if holder.get_type() == "ipbus":
                    self._assert_matches(
                        holder.hdr.generate_ipbus_addr_table(),
                        base + ".xml",
                        "xml ipbus addr table must match manual file",
                    )

    ############## Documentation Testing ##################

    def test_doc(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing Doc generation...")
                self._assert_matches(
                    holder.doc.generate_tex_documentation("1.0.0-dev"),
                    "example/example_{0}/doc/example_{0}.tex".format(
                        holder.bus.bus_type
                    ),
                    "doc must match manual file",
                )

    ############## Prototype (full access-mode coverage) ##################

    def test_prototype_hdl(self):
        """The prototype exercises the full bust 1.0 access-mode system over both
        buses from a single register map."""
        self.logger.info("Testing prototype local-bus HDL generation...")
        _, axi_mod, _, _ = _load_prototype("axi")
        _, ipbus_mod, _, _ = _load_prototype("ipbus")
        hdl = "example/example_prototype/hdl"
        self._assert_matches(
            GeneratorFactory.generate_localbus_package_vhdl(axi_mod),
            hdl + "/localbus_pkg.vhd",
            "prototype local-bus package must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_regfile_package_vhdl(axi_mod),
            hdl + "/prototype_regfile_pkg.vhd",
            "prototype regfile package must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_regfile_vhdl(axi_mod),
            hdl + "/prototype_regfile.vhd",
            "prototype regfile must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_axi_endpoint_vhdl(axi_mod),
            hdl + "/prototype_axi_endpoint.vhd",
            "prototype axi endpoint must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_ipb_endpoint_vhdl(ipbus_mod),
            hdl + "/prototype_ipb_endpoint.vhd",
            "prototype ipb endpoint must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(axi_mod),
            hdl + "/prototype.vhd",
            "prototype axi top must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(ipbus_mod),
            hdl + "/prototype_ipbus.vhd",
            "prototype ipbus top must match manual file",
        )

    def test_prototype_tb(self):
        self.logger.info("Testing prototype testbench generation...")
        _, axi_mod, _, _ = _load_prototype("axi")
        _, ipbus_mod, _, _ = _load_prototype("ipbus")
        hdl = "example/example_prototype/hdl"
        self._assert_matches(
            GeneratorFactory.generate_localbus_axi_testbench_vhdl(axi_mod),
            hdl + "/prototype_tb.vhd",
            "prototype axi testbench must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_localbus_ipbus_testbench_vhdl(ipbus_mod),
            hdl + "/prototype_ipbus_tb.vhd",
            "prototype ipbus testbench must match manual file",
        )

    def test_prototype_hdr(self):
        self.logger.info("Testing prototype header generation...")
        _, _, _, hdr = _load_prototype("axi")
        base = "example/example_prototype/header/prototype"
        self._assert_matches(
            hdr.generate_c_header(), base + ".h", "prototype c header must match"
        )
        self._assert_matches(
            hdr.generate_cpp_header(), base + ".hpp", "prototype cpp header must match"
        )
        self._assert_matches(
            hdr.generate_python_header(),
            base + ".py",
            "prototype python header must match",
        )


if __name__ == "__main__":
    unittest.main()
