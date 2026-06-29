"""Output file generation module for bust.

This module handles the creation of all output files: the local-bus VHDL stack
(regfile package, regfile, bus endpoint, top wrapper) and its UVVM testbench,
language headers, and documentation. It manages the directory structure and
coordinates file generation from the Module, Bus, Header, and Documentation
instances.
"""

import os
import logging
import subprocess

from bust.generators.factory import GeneratorFactory
from bust.utils.file_utils import write_string_to_file

logger = logging.getLogger(__name__)

# Per-bus endpoint and testbench generators. Adding a bus is a new entry plus
# its templates; the file name comes from the bus's endpoint_suffix.
_ENDPOINT_GENERATORS = {
    "axi": GeneratorFactory.generate_axi_endpoint_vhdl,
    "ipbus": GeneratorFactory.generate_ipb_endpoint_vhdl,
    "sbi": GeneratorFactory.generate_sbi_endpoint_vhdl,
    "avalon": GeneratorFactory.generate_avalon_endpoint_vhdl,
}
_TESTBENCH_GENERATORS = {
    "axi": GeneratorFactory.generate_localbus_axi_testbench_vhdl,
    "ipbus": GeneratorFactory.generate_localbus_ipbus_testbench_vhdl,
    "sbi": GeneratorFactory.generate_localbus_sbi_testbench_vhdl,
    "avalon": GeneratorFactory.generate_localbus_avalon_testbench_vhdl,
}


def generate_output(settings, bus, module, header, documentation, gen_settings):
    """Generate all output files for a bus slave module.

    Creates directory structure and writes the local-bus VHDL stack,
    documentation, and language headers based on configuration.

    Args:
        settings: Settings instance with paths and configuration.
        bus: Bus instance with interface configuration.
        module: Module instance with register definitions.
        header: Header instance for generating language headers.
        documentation: Documentation instance for generating docs.
        gen_settings: Dictionary with generation options:
            - dir: Output directory path
            - force_ow: Force overwrite without prompting
            - gen_localbus: Generate the local-bus VHDL stack and testbench
            - gen_header: Generate language headers
            - gen_doc: Generate documentation
            - gen_pdf: Generate PDF from LaTeX

    Raises:
        Exception: If file generation fails.
    """

    # Control all output directories
    proj_dir = os.path.expanduser(gen_settings["dir"])  # Make sure that we understand ~
    logger.info(f"Project path: {os.path.abspath(proj_dir)}")
    if settings.mod_subdir:
        mod_dir = os.path.join(proj_dir, module.name)
    else:
        mod_dir = proj_dir

    mod_hdl = os.path.join(mod_dir, settings.hdl_dir)
    mod_tb = os.path.join(mod_dir, settings.tb_dir)
    mod_doc = os.path.join(mod_dir, settings.doc_dir)
    mod_header = os.path.join(mod_dir, settings.header_dir)

    logger.debug("Creating all output directories")
    try:
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(mod_dir, exist_ok=True)
        os.makedirs(mod_hdl, exist_ok=True)
        os.makedirs(mod_tb, exist_ok=True)
        os.makedirs(mod_doc, exist_ok=True)
        os.makedirs(mod_header, exist_ok=True)

    except Exception as e:
        logger.error("ERROR: Could not create output directories")
        logger.error(e)

    else:
        logger.debug("Successfully created all output directories")

    if gen_settings.get("gen_localbus"):
        logger.info("Generating local-bus VHDL files...")
        try:
            filename = "localbus_pkg.vhd"
            write_string_to_file(
                GeneratorFactory.generate_localbus_package_vhdl(module),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )
            filename = f"{module.name}_regfile_pkg.vhd"
            write_string_to_file(
                GeneratorFactory.generate_regfile_package_vhdl(module),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )
            filename = f"{module.name}_regfile.vhd"
            write_string_to_file(
                GeneratorFactory.generate_regfile_vhdl(module),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )
            endpoint_generator = _ENDPOINT_GENERATORS.get(bus.bus_type)
            if endpoint_generator is not None:
                endpoint = endpoint_generator(module)
                filename = f"{module.name}_{bus.endpoint_suffix}.vhd"
                write_string_to_file(
                    endpoint, filename, mod_hdl, gen_settings["force_ow"]
                )
                filename = f"{module.name}.vhd"
                write_string_to_file(
                    GeneratorFactory.generate_module_top_vhdl(module),
                    filename,
                    mod_hdl,
                    gen_settings["force_ow"],
                )
                testbench_generator = _TESTBENCH_GENERATORS.get(bus.bus_type)
                if testbench_generator is not None:
                    testbench = testbench_generator(module)
                    write_string_to_file(
                        testbench,
                        f"{module.name}_tb.vhd",
                        mod_tb,
                        gen_settings["force_ow"],
                    )
        except Exception:
            logger.error("ERROR: Could not generate local-bus VHDL files")
            raise

    if gen_settings["gen_header"]:
        logger.info("Generating Module Include Files...")
        try:
            filename = f"{module.name}.h"
            write_string_to_file(
                header.generate_c_header(),
                filename,
                mod_header,
                gen_settings["force_ow"],
            )
            filename = f"{module.name}.hpp"
            write_string_to_file(
                header.generate_cpp_header(),
                filename,
                mod_header,
                gen_settings["force_ow"],
            )
            filename = f"{module.name}.py"
            write_string_to_file(
                header.generate_python_header(),
                filename,
                mod_header,
                gen_settings["force_ow"],
            )
            if bus.bus_type == "ipbus":
                filename = f"{module.name}.xml"
                write_string_to_file(
                    header.generate_ipbus_addr_table(),
                    filename,
                    mod_header,
                    gen_settings["force_ow"],
                )

        except Exception as e:
            logger.error("ERROR: Could not generate Module Include Files")
            raise e

    if gen_settings["gen_doc"]:
        logger.info("Generating Module Documentation...")
        try:
            filename = f"{module.name}.tex"
            write_string_to_file(
                documentation.generate_tex_documentation(),
                filename,
                mod_doc,
                gen_settings["force_ow"],
            )
        except Exception as e:
            logger.error("ERROR: Could not generate Module Documentation")
            raise e

    if gen_settings["gen_pdf"]:
        logger.info("Generating Documentation PDF...")
        try:
            subprocess.call(
                [
                    "pdflatex",
                    "--interaction=batchmode",
                    f"--output-directory={mod_doc}",
                    os.path.join(mod_doc, module.name + ".tex"),
                ],
                stdout=open(os.devnull, "wb"),
            )
        except Exception:
            logger.error("ERROR: PDF Generation Failed")
