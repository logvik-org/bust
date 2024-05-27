import os
import logging
import subprocess

from bust.utils import write_string_to_file, update_module_top_level

logger = logging.getLogger(__name__)


def generate_output(
    settings, bus, module, header, documentation, testbench, gen_settings
):
    """Starts the generation of all output files"""

    # Control all output directories
    proj_dir = os.path.expanduser(gen_settings["dir"])  # Make sure that we understand ~
    logger.info("Project path: {}".format(os.path.abspath(proj_dir)))
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

    except Exception:
        logger.error("ERROR: Could not create output directories")
        exit(1)
    else:
        logger.debug("Successfully created all output directories")

    if gen_settings["gen_bus"]:
        logger.info("Generating Bus VHDL Package File...")
        try:
            filename = "{}_pkg.vhd".format(bus.bus_type)
            write_string_to_file(
                bus.return_bus_pkg_VHDL(), filename, bus_hdl, gen_settings["force_ow"]
            )
        except Exception:
            logger.error("ERROR: Could not generate Bus VHDL Package File")
            exit(1)

    if gen_settings["gen_mod"]:
        logger.info("Generating Module VHDL Files...")
        try:
            # PIF
            filename = "{}_{}_pif.vhd".format(module.name, bus.short_name)
            write_string_to_file(
                bus.return_bus_pif_VHDL(module),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )
            # PIF Package
            filename = "{}_pif_pkg.vhd".format(module.name)
            write_string_to_file(
                module.return_module_pkg_VHDL(),
                filename,
                mod_hdl,
                gen_settings["force_ow"],
            )

            # Top Module
            filename = "{}.vhd".format(module.name)
            if gen_settings["update_top"]:
                logger.info("Trying to update top level-file")
                path = os.path.join(mod_hdl, filename)
                new_top = update_module_top_level(path, module.return_module_VHDL())
                write_string_to_file(
                    new_top, filename, mod_hdl, gen_settings["force_ow_top"]
                )
            else:
                write_string_to_file(
                    module.return_module_VHDL(),
                    filename,
                    mod_hdl,
                    gen_settings["force_ow_top"],
                )

        except Exception:
            logger.error("ERROR: Could not generate Module VHDL Files")
            exit(1)

    if gen_settings["gen_header"]:
        logger.info("Generating Module Include Files...")
        try:
            filename = "{}.h".format(module.name)
            write_string_to_file(
                header.return_c_header(), filename, mod_header, gen_settings["force_ow"]
            )
            filename = "{}.hpp".format(module.name)
            write_string_to_file(
                header.return_cpp_header(),
                filename,
                mod_header,
                gen_settings["force_ow"],
            )
            filename = "{}.py".format(module.name)
            write_string_to_file(
                header.return_python_header(),
                filename,
                mod_header,
                gen_settings["force_ow"],
            )
            if bus.bus_type == "ipbus":
                filename = "{}.xml".format(module.name)
                write_string_to_file(
                    header.return_ipbus_addr_table(),
                    filename,
                    mod_header,
                    gen_settings["force_ow"],
                )

        except Exception:
            logger.error("ERROR: Could not generate Module Include Files")
            exit(1)

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
                    testbench.return_uvvm_component_list(),
                    filename,
                    mod_script,
                    gen_settings["force_ow"],
                )
                filename = "simulate_{}_pif.do".format(bus.bus_type)
                write_string_to_file(
                    testbench.return_tcl_script(),
                    filename,
                    mod_script,
                    gen_settings["force_ow"],
                )
                filename = "{}_{}_pif_tb.vhd".format(module.name, bus.short_name)
                write_string_to_file(
                    testbench.return_vhdl_tb(),
                    filename,
                    mod_tb,
                    gen_settings["force_ow"],
                )

            except Exception:
                logger.error("ERROR: Could not generate PIF Testbench Files")
                exit(1)

    if gen_settings["gen_doc"]:
        logger.info("Generating Module Documentation...")
        try:
            filename = "{}.tex".format(module.name)
            write_string_to_file(
                documentation.return_tex_documentation(),
                filename,
                mod_doc,
                gen_settings["force_ow"],
            )
        except Exception:
            logger.error("ERROR: Could not generate Module Documentation")
            exit(1)

    if gen_settings["gen_pdf"]:
        logger.info("Generating Documentation PDF...")
        try:
            subprocess.call(
                [
                    "pdflatex",
                    "--output-directory=" + mod_doc,
                    os.path.join(mod_doc, module.name + ".tex"),
                ],
                stdout=open(os.devnull, "wb"),
            )
        except Exception:
            logger.error("ERROR: PDF Generation Failed")
            exit(1)
