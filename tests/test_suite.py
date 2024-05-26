import unittest
import logging.config
from bust.utils import json_parser
from bust.module import Module
from bust.bus import Bus
from bust.settings import Settings
from bust.testbench import Testbench
from bust.documentation import Documentation
from bust.header import Header


class BusHolder:
    def __init__(self, bus_type):
        self.sett, self.bus, self.mod, self.tb, self.doc, self.hdr = self.load_bus(
            bus_type
        )

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
        tb = Testbench(mod, bus.get_VHDL_generator(), sett)
        doc = Documentation(mod)
        hdr = Header(mod)
        return sett, bus, mod, tb, doc, hdr

    def __repr__(self):
        return self.get_type()


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

    ############## Module Testing ##################

    def test_pif(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing PIF generation...")
                with open(
                    "example/example_{0}/hdl/example_{0}_pif_pkg.vhd".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.mod.return_module_pkg_VHDL(),
                    string,
                    "pif pkg must match manual file",
                )

                with open(
                    "example/example_{0}/hdl/example_{0}_{1}_pif.vhd".format(
                        holder.bus.bus_type, holder.bus.short_name
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.bus.return_bus_pif_VHDL(holder.mod),
                    string,
                    "pif must match manual file",
                )

    def test_module(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing Module generation...")
                with open(
                    "example/example_{0}/hdl/example_{0}.vhd".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.mod.return_module_VHDL(),
                    string,
                    "module must match manual file",
                )

    def test_buspkg(self):
        holder = BusHolder("axi")
        # Only for AXI
        self.logger.info("Testing Bus PKG generation...")
        with open("example/example_axi/hdl/axi_pkg.vhd") as f:
            string = f.read()
        self.assertEqual(
            holder.bus.return_bus_pkg_VHDL(), string, "bus pkg must match manual file"
        )

    ############## Testbench Testing ##################

    def test_bench_scripts(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):

                self.logger.info("Testing TB Script generation...")
                with open(
                    "example/example_{}/scripts/simulate_{}_pif.do".format(
                        holder.bus.bus_type, holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.tb.return_tcl_script(),
                    string,
                    ".tcl script must match manual file",
                )

                with open(
                    "example/example_{}/scripts/component_list.txt".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.tb.return_uvvm_component_list(),
                    string,
                    ".txt file must match manual file",
                )

    def test_bench_hdl(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing TB Sequencer generation...")
                with open(
                    "example/example_{0}/tb/example_{0}_{1}_pif_tb.vhd".format(
                        holder.bus.bus_type, holder.bus.short_name
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.tb.return_vhdl_tb(), string, ".vhd TB must match manual file"
                )

    ############## Header Testing ##################

    def test_hdr(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing Header generation...")
                with open(
                    "example/example_{0}/header/example_{0}.h".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.hdr.return_c_header(),
                    string,
                    "c header must match manual file",
                )

                with open(
                    "example/example_{0}/header/example_{0}.hpp".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.hdr.return_cpp_header(),
                    string,
                    "c++ header must match manual file",
                )

                with open(
                    "example/example_{0}/header/example_{0}.py".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.hdr.return_python_header(),
                    string,
                    "python header must match manual file",
                )

                if holder.get_type() == "ipbus":
                    with open(
                        "example/example_{0}/header/example_{0}.xml".format(
                            holder.bus.bus_type
                        )
                    ) as f:
                        string = f.read()
                    self.assertEqual(
                        holder.hdr.return_ipbus_addr_table(),
                        string,
                        "python header must match manual file",
                    )

    ############## Header Testing ##################

    def test_doc(self):
        for holder in self.buzz:
            with self.subTest(holder=holder):
                self.logger.info("Testing Doc generation...")
                with open(
                    "example/example_{0}/doc/example_{0}.tex".format(
                        holder.bus.bus_type
                    )
                ) as f:
                    string = f.read()
                self.assertEqual(
                    holder.doc.return_tex_documentation("0.9.4"),
                    string,
                    "doc must match manual file",
                )


if __name__ == "__main__":
    unittest.main()
