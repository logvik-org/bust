import logging.config
import os
import unittest

from bust.utils.json_utils import json_parser
from bust.core.module import Module
from bust.core.bus import Bus
from bust.settings import Settings
from bust.generators.documentation_generator import DocumentationGenerator
from bust.generators.header_generator import HeaderGenerator
from bust.generators.factory import GeneratorFactory

# BUST_UPDATE_GOLDENS=1 rewrites the committed example outputs from the current
# generator instead of comparing against them. Review the diff before committing.
_UPDATE_GOLDENS = os.environ.get("BUST_UPDATE_GOLDENS") == "1"


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
        sett = Settings(json_file)
        bus = Bus(json["bus"])
        mod = Module(json["module"], bus, sett)
        doc = DocumentationGenerator(mod)
        hdr = HeaderGenerator(mod)
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
    return bus, mod, DocumentationGenerator(mod), HeaderGenerator(mod)


def _load_access_matrix():
    """The access-mode combination example, one register per combination class."""
    json = json_parser("example/example_access_matrix.json")
    mod = Module(json["module"], Bus(json["bus"]), settings=None)
    return mod, HeaderGenerator(mod)


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
        if _UPDATE_GOLDENS:
            with open(path, "w") as f:
                f.write(generated)
            return
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
                    base + "_localbus_pkg.vhd",
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
                    "starter top level must match manual file",
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
                base = "example/example_{0}/doc/example_{0}".format(holder.bus.bus_type)
                self._assert_matches(
                    holder.doc.generate_tex_documentation("1.0.0-dev"),
                    base + ".tex",
                    "doc must match manual file",
                )
                self._assert_matches(
                    holder.doc.generate_html_documentation("1.0.0-dev"),
                    base + ".html",
                    "html doc must match manual file",
                )
                self._assert_matches(
                    holder.doc.generate_markdown_documentation("1.0.0-dev"),
                    base + ".md",
                    "markdown doc must match manual file",
                )

    ############## Prototype (full access-mode coverage) ##################

    def test_prototype_hdl(self):
        """The prototype exercises the full bust 1.0 access-mode system over both
        buses from a single register map."""
        self.logger.info("Testing prototype local-bus HDL generation...")
        _, axi_mod, _, _ = _load_prototype("axi")
        _, ipbus_mod, _, _ = _load_prototype("ipbus")
        _, sbi_mod, _, _ = _load_prototype("sbi")
        _, avalon_mod, _, _ = _load_prototype("avalon")
        _, wishbone_mod, _, _ = _load_prototype("wishbone")
        _, apb_mod, _, _ = _load_prototype("apb")
        hdl = "example/example_prototype/hdl"
        self._assert_matches(
            GeneratorFactory.generate_localbus_package_vhdl(axi_mod),
            hdl + "/prototype_localbus_pkg.vhd",
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
            GeneratorFactory.generate_sbi_endpoint_vhdl(sbi_mod),
            hdl + "/prototype_sbi_endpoint.vhd",
            "prototype sbi endpoint must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_avalon_endpoint_vhdl(avalon_mod),
            hdl + "/prototype_avalon_endpoint.vhd",
            "prototype avalon endpoint must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_wishbone_endpoint_vhdl(wishbone_mod),
            hdl + "/prototype_wishbone_endpoint.vhd",
            "prototype wishbone endpoint must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_apb_endpoint_vhdl(apb_mod),
            hdl + "/prototype_apb_endpoint.vhd",
            "prototype apb endpoint must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(axi_mod),
            hdl + "/prototype.vhd",
            "prototype axi starter must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(ipbus_mod),
            hdl + "/prototype_ipbus.vhd",
            "prototype ipbus starter must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(sbi_mod),
            hdl + "/prototype_sbi.vhd",
            "prototype sbi starter must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(avalon_mod),
            hdl + "/prototype_avalon.vhd",
            "prototype avalon starter must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(wishbone_mod),
            hdl + "/prototype_wishbone.vhd",
            "prototype wishbone starter must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_module_top_vhdl(apb_mod),
            hdl + "/prototype_apb.vhd",
            "prototype apb starter must match manual file",
        )

    def test_prototype_tb(self):
        self.logger.info("Testing prototype testbench generation...")
        _, axi_mod, _, _ = _load_prototype("axi")
        _, ipbus_mod, _, _ = _load_prototype("ipbus")
        _, sbi_mod, _, _ = _load_prototype("sbi")
        _, avalon_mod, _, _ = _load_prototype("avalon")
        _, wishbone_mod, _, _ = _load_prototype("wishbone")
        _, apb_mod, _, _ = _load_prototype("apb")
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
        # IPBus counts addresses in 32-bit words, so the IPBus build of the
        # prototype has other register offsets than the AXI build. The IPBus sim
        # target compiles this package with the IPBus testbench above. The
        # register file itself is the same for every bus.
        self._assert_matches(
            GeneratorFactory.generate_regfile_package_vhdl(ipbus_mod),
            hdl + "/prototype_ipbus_regfile_pkg.vhd",
            "prototype ipbus regfile package must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_localbus_sbi_testbench_vhdl(sbi_mod),
            hdl + "/prototype_sbi_tb.vhd",
            "prototype sbi testbench must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_localbus_avalon_testbench_vhdl(avalon_mod),
            hdl + "/prototype_avalon_tb.vhd",
            "prototype avalon testbench must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_localbus_wishbone_testbench_vhdl(wishbone_mod),
            hdl + "/prototype_wishbone_tb.vhd",
            "prototype wishbone testbench must match manual file",
        )
        self._assert_matches(
            GeneratorFactory.generate_localbus_apb_testbench_vhdl(apb_mod),
            hdl + "/prototype_apb_tb.vhd",
            "prototype apb testbench must match manual file",
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

    def test_prototype_doc(self):
        _, _, doc, _ = _load_prototype("axi")
        self._assert_matches(
            doc.generate_tex_documentation("1.0.0-dev"),
            "example/example_prototype/doc/prototype.tex",
            "prototype doc must match manual file",
        )
        self._assert_matches(
            doc.generate_html_documentation("1.0.0-dev"),
            "example/example_prototype/doc/prototype.html",
            "prototype html doc must match manual file",
        )
        self._assert_matches(
            doc.generate_markdown_documentation("1.0.0-dev"),
            "example/example_prototype/doc/prototype.md",
            "prototype markdown doc must match manual file",
        )

    ############## Access-mode combination matrix ##################

    def test_access_matrix_hdl_and_tb(self):
        self.logger.info("Testing access-matrix HDL and testbench generation...")
        mod, _ = _load_access_matrix()
        hdl = "example/example_access_matrix/hdl"
        for generated, name in (
            (
                GeneratorFactory.generate_localbus_package_vhdl(mod),
                "access_matrix_localbus_pkg.vhd",
            ),
            (
                GeneratorFactory.generate_regfile_package_vhdl(mod),
                "access_matrix_regfile_pkg.vhd",
            ),
            (GeneratorFactory.generate_regfile_vhdl(mod), "access_matrix_regfile.vhd"),
            (
                GeneratorFactory.generate_axi_endpoint_vhdl(mod),
                "access_matrix_axi_endpoint.vhd",
            ),
            (GeneratorFactory.generate_module_top_vhdl(mod), "access_matrix.vhd"),
            (
                GeneratorFactory.generate_localbus_axi_testbench_vhdl(mod),
                "access_matrix_tb.vhd",
            ),
        ):
            with self.subTest(file=name):
                self._assert_matches(
                    generated, f"{hdl}/{name}", f"access_matrix {name} must match"
                )

    def test_access_matrix_hdr(self):
        self.logger.info("Testing access-matrix header generation...")
        _, hdr = _load_access_matrix()
        base = "example/example_access_matrix/header/access_matrix"
        for generated, ext in (
            (hdr.generate_c_header(), ".h"),
            (hdr.generate_cpp_header(), ".hpp"),
            (hdr.generate_python_header(), ".py"),
        ):
            with self.subTest(file=ext):
                self._assert_matches(
                    generated, base + ext, f"access_matrix {ext} header must match"
                )


if __name__ == "__main__":
    unittest.main()
