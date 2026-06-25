"""Output file generation module for bust.

This module handles the creation of all output files including VHDL code,
testbenches, documentation, headers, and simulation scripts. It manages
directory structure and coordinates file generation from Module, Bus,
Header, Documentation, and Testbench instances.
"""

import os
import logging
import subprocess

from bust.generators.factory import GeneratorFactory
from bust.utils.file_utils import write_string_to_file, update_module_top_level

logger = logging.getLogger(__name__)


def generate_output(
    settings, bus, module, header, documentation, testbench, gen_settings
):
    """Generate all output files for a bus slave module.

    Creates directory structure and writes VHDL files, testbenches,
    documentation, headers, and scripts based on configuration.

    Args:
        settings: Settings instance with paths and configuration.
        bus: Bus instance with interface configuration.
        module: Module instance with register definitions.
        header: Header instance for generating language headers.
        documentation: Documentation instance for generating docs.
        testbench: Testbench instance for generating test files.
        gen_settings: Dictionary with generation options:
            - dir: Output directory path
            - force_ow: Force overwrite without prompting
            - gen_bus: Generate bus VHDL package
            - gen_mod: Generate module VHDL files
            - update_top: Update existing top-level preserving user code
            - force_ow_top: Force overwrite top-level
            - gen_tb: Generate testbench
            - gen_doc: Generate documentation
            - gen_hdr: Generate language headers
            - format_vhdl: Run VHDL formatter

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

    if settings.bus_subdir and not bus.bus_type == "ipbus":
        bus_dir = os.path.join(proj_dir, bus.bus_type)
    else:
        bus_dir = mod_dir

    mod_hdl = os.path.join(mod_dir, settings.hdl_dir)
    mod_script = os.path.join(mod_dir, settings.script_dir)
    mod_tb = os.path.join(mod_dir, settings.tb_dir)
    mod_doc = os.path.join(mod_dir, settings.doc_dir)
    mod_header = os.path.join(mod_dir, settings.header_dir)
    mod_sim = os.path.join(mod_dir, settings.sim_dir)
    bus_hdl = os.path.join(bus_dir, settings.hdl_dir)
    bus_sim = os.path.join(bus_dir, settings.sim_dir)

    logger.debug("Creating all output directories")
    try:
        os.makedirs(proj_dir, exist_ok=True)
        os.makedirs(mod_dir, exist_ok=True)
        os.makedirs(bus_dir, exist_ok=True)
        os.makedirs(mod_hdl, exist_ok=True)
        os.makedirs(mod_script, exist_ok=True)
        os.makedirs(mod_tb, exist_ok=True)
        os.makedirs(mod_doc, exist_ok=True)
        os.makedirs(mod_header, exist_ok=True)
        os.makedirs(mod_sim, exist_ok=True)
        os.makedirs(bus_hdl, exist_ok=True)
        os.makedirs(bus_sim, exist_ok=True)

    except Exception as e:
        logger.error("ERROR: Could not create output directories")
        logger.error(e)

    else:
        logger.debug("Successfully created all output directories")

    if gen_settings["gen_bus"]:
        logger.info("Generating Bus VHDL Package File...")
        try:
            filename = f"{bus.bus_type}_pkg.vhd"
            write_string_to_file(
                GeneratorFactory.generate_bus_package_vhdl(bus),
                filename,
                bus_hdl,
                gen_settings["force_ow"],
            )
        except Exception as e:
            logger.error("ERROR: Could not generate Bus VHDL Package File")
            raise e

    if gen_settings["gen_mod"]:
        logger.info("Generating Module VHDL Files...")
        try:
            # PIF
            filename = f"{module.name}_{bus.short_name}_pif.vhd"
            write_string_to_file(
                GeneratorFactory.generate_bus_pif_vhdl(bus, module),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )
            # PIF Package
            filename = f"{module.name}_pif_pkg.vhd"
            write_string_to_file(
                GeneratorFactory.generate_module_package_vhdl(module),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )

            # Top Module
            filename = f"{module.name}.vhd"
            if gen_settings["update_top"]:
                logger.info("Trying to update top level-file")
                path = os.path.join(mod_hdl, filename)
                new_top = update_module_top_level(
                    path, GeneratorFactory.generate_module_vhdl(module)
                )
                write_string_to_file(
                    new_top, filename, mod_hdl, gen_settings["force_ow_top"]
                )
            else:
                write_string_to_file(
                    GeneratorFactory.generate_module_vhdl(module),
                    filename,
                    mod_hdl,
                    gen_settings["force_ow_top"],
                )

        except Exception as e:
            logger.error("ERROR: Could not generate Module VHDL Files")
            raise e

    if gen_settings.get("gen_localbus"):
        logger.info("Generating local-bus VHDL files (experimental)...")
        try:
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
            if bus.bus_type == "axi":
                endpoint = GeneratorFactory.generate_axi_endpoint_vhdl(module)
                filename = f"{module.name}_axi_endpoint.vhd"
            elif bus.bus_type == "ipbus":
                endpoint = GeneratorFactory.generate_ipb_endpoint_vhdl(module)
                filename = f"{module.name}_ipb_endpoint.vhd"
            else:
                endpoint = None
            if endpoint is not None:
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

    if gen_settings["gen_tb"]:
        if settings.uvvm_rel_path is None:
            logger.error(
                "Cannot generate testbench: UVVM Relative Path is not specified"
            )
        else:
            logger.info("Generating PIF Testbench Files...")
            try:
                filename = "component_list.txt"
                write_string_to_file(
                    testbench.generate_uvvm_component_list(),
                    filename,
                    mod_script,
                    gen_settings["force_ow"],
                )
                filename = f"simulate_{bus.bus_type}_pif.do"
                write_string_to_file(
                    testbench.generate_tcl_script(),
                    filename,
                    mod_script,
                    gen_settings["force_ow"],
                )
                filename = f"{module.name}_{bus.short_name}_pif_tb.vhd"
                write_string_to_file(
                    testbench.generate_vhdl_testbench(),
                    filename,
                    mod_tb,
                    gen_settings["force_ow"],
                )

            except Exception as e:
                logger.error("ERROR: Could not generate PIF Testbench Files")
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
