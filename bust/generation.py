"""Output file generation module for bust.

This module handles the creation of all output files: the local-bus VHDL stack
(regfile package, regfile, bus endpoint), the starter top level the user owns,
the UVVM testbench, language headers, and documentation. It manages the directory structure and
coordinates file generation from the Module, Bus, Header, and Documentation
instances.
"""

import os
import logging
import shutil
import subprocess
import sys
from typing import Any, Dict, Optional, Union

from bust.core.bus import Bus
from bust.core.module import Module
from bust.exceptions import FormatError
from bust.generators.documentation_generator import DocumentationGenerator
from bust.generators.factory import GeneratorFactory
from bust.generators.header_generator import HeaderGenerator
from bust.interaction import ConsoleInteractionHandler
from bust.settings import Settings
from bust.utils.file_utils import write_string_to_file
from bust.utils.json_utils import parse_json_text
from bust.validation.schema_check import check_register_map

logger = logging.getLogger(__name__)

# Per-bus endpoint and testbench generators. Adding a bus is a new entry plus
# its templates; the file name comes from the bus's endpoint_suffix.
_ENDPOINT_GENERATORS = {
    "axi": GeneratorFactory.generate_axi_endpoint_vhdl,
    "ipbus": GeneratorFactory.generate_ipb_endpoint_vhdl,
    "sbi": GeneratorFactory.generate_sbi_endpoint_vhdl,
    "avalon": GeneratorFactory.generate_avalon_endpoint_vhdl,
    "wishbone": GeneratorFactory.generate_wishbone_endpoint_vhdl,
    "apb": GeneratorFactory.generate_apb_endpoint_vhdl,
}
_TESTBENCH_GENERATORS = {
    "axi": GeneratorFactory.generate_localbus_axi_testbench_vhdl,
    "ipbus": GeneratorFactory.generate_localbus_ipbus_testbench_vhdl,
    "sbi": GeneratorFactory.generate_localbus_sbi_testbench_vhdl,
    "avalon": GeneratorFactory.generate_localbus_avalon_testbench_vhdl,
    "wishbone": GeneratorFactory.generate_localbus_wishbone_testbench_vhdl,
    "apb": GeneratorFactory.generate_localbus_apb_testbench_vhdl,
}


def top_level_path(module: Module, settings: Optional[Settings] = None) -> str:
    """The key of the starter <module>.vhd in the outputs of `module`."""
    settings = settings or Settings(None)
    return f"{module.name}/{settings.hdl_dir}/{module.name}.vhd"


def module_outputs(
    module: Module,
    settings: Optional[Settings] = None,
    localbus: bool = True,
    headers: bool = True,
    documentation: bool = True,
) -> Dict[str, str]:
    """Render the output files of `module` without writing them.

    Args:
        module: Module instance with register definitions.
        settings: Names the hdl, tb, header and doc directories.
        localbus: Include the local-bus VHDL stack, the starter top level and
            the testbench.
        headers: Include the language headers.
        documentation: Include the LaTeX and HTML documentation.

    Returns:
        The content of each file by its path relative to the output directory,
        such as ``uart/hdl/uart_regfile.vhd``, in the order the CLI writes them.
        The paths use ``/`` on every platform.
    """
    settings = settings or Settings(None)
    name = module.name
    hdl = f"{name}/{settings.hdl_dir}"
    outputs: Dict[str, str] = {}
    if localbus:
        generate_endpoint = _ENDPOINT_GENERATORS[module.bus.bus_type]
        generate_testbench = _TESTBENCH_GENERATORS[module.bus.bus_type]
        outputs[f"{hdl}/{name}_localbus_pkg.vhd"] = (
            GeneratorFactory.generate_localbus_package_vhdl(module)
        )
        outputs[f"{hdl}/{name}_regfile_pkg.vhd"] = (
            GeneratorFactory.generate_regfile_package_vhdl(module)
        )
        outputs[f"{hdl}/{name}_regfile.vhd"] = GeneratorFactory.generate_regfile_vhdl(
            module
        )
        outputs[f"{hdl}/{name}_{module.bus.endpoint_suffix}.vhd"] = generate_endpoint(
            module
        )
        outputs[top_level_path(module, settings)] = (
            GeneratorFactory.generate_module_top_vhdl(module)
        )
        outputs[f"{name}/{settings.tb_dir}/{name}_tb.vhd"] = generate_testbench(module)
    if headers:
        header = HeaderGenerator(module)
        base = f"{name}/{settings.header_dir}/{name}"
        outputs[f"{base}.h"] = header.generate_c_header()
        outputs[f"{base}.hpp"] = header.generate_cpp_header()
        outputs[f"{base}.py"] = header.generate_python_header()
        if module.bus.bus_type == "ipbus":
            outputs[f"{base}.xml"] = header.generate_ipbus_addr_table()
    if documentation:
        doc = DocumentationGenerator(module)
        base = f"{name}/{settings.doc_dir}/{name}"
        outputs[f"{base}.tex"] = doc.generate_tex_documentation()
        outputs[f"{base}.html"] = doc.generate_html_documentation()
    return outputs


def generate_files(register_map: Union[str, Dict[str, Any]]) -> Dict[str, str]:
    """Render every output file of a register map, without touching the disk.

    The paths and contents are the ones `bust FILE -o DIR -p` writes under DIR.
    The starter top level, at `top_level_path`, is always included. The CLI
    writes it only when the file is missing, and a caller that keeps files
    should do the same, since the user edits that file.

    Args:
        register_map: The JSON or JSON5 text of a register map, or the register
            map as `json.loads` returns it.

    Returns:
        The content of each file by its path, see `module_outputs`.

    Raises:
        FormatError: If the register map does not parse or breaks the schema.
            The message lists every problem.
        RuntimeError: If bust rejects the register map, such as two registers
            at one address.
    """
    if isinstance(register_map, str):
        data = parse_json_text(register_map, "<register map>")
        report = check_register_map(data, register_map)
    else:
        data = register_map
        report = check_register_map(data)
    if report.errors:
        raise FormatError("\n".join(str(problem) for problem in report.errors))
    module = Module(data["module"], Bus(data["bus"]), Settings(None))
    return module_outputs(module)


def _write_top(path, starter, gen_settings):
    """Write the starter <module>.vhd if it is missing, or replace it if asked.

    <module>.vhd is the user's file. bust writes a starter once and does not
    change the file again, not even with -f. With replace_top it writes a fresh
    starter and keeps the old file as <module>.vhd.bak.
    """
    mod_hdl, filename = os.path.split(path)
    if not os.path.isfile(path):
        write_string_to_file(starter, filename, mod_hdl, True)
        logger.info(
            f"Wrote {path}, a starting point that is yours to edit. "
            "bust will not change it again."
        )
    elif gen_settings.get("replace_top"):
        backup = path + ".bak"
        if not gen_settings["force_ow"]:
            if not sys.stdin.isatty():
                raise FileExistsError(
                    f"There is no terminal to ask whether to replace {path}. "
                    "Run bust with --replace-top -f to replace it."
                )
            answer = ConsoleInteractionHandler()(
                f"Replace {path} with a fresh starter and keep the old file as "
                f"{backup}? (y/N):"
            )
            if answer.upper() != "Y":
                logger.warning(f"Did not replace {path}")
                return
        shutil.copyfile(path, backup)
        write_string_to_file(starter, filename, mod_hdl, True)
        logger.info(f"Replaced {path} with a fresh starter. The old file is {backup}.")
    elif gen_settings["force_ow"]:
        logger.info(
            f"{path} is yours, so -f did not replace it. To replace it with a "
            "fresh starter, run bust with --replace-top."
        )


def generate_output(settings, module, gen_settings):
    """Write the output files of a module, and build the PDF if asked.

    Args:
        settings: Settings instance with paths and configuration.
        module: Module instance with register definitions.
        gen_settings: Dictionary with generation options:
            - dir: Output directory path
            - force_ow: Force overwrite without prompting
            - replace_top: Replace the user's <module>.vhd with a fresh starter
            - gen_localbus: Generate the local-bus VHDL stack and testbench
            - gen_header: Generate language headers
            - gen_doc: Generate documentation
            - gen_pdf: Generate PDF from LaTeX, if pdflatex is installed
    """
    proj_dir = os.path.expanduser(gen_settings["dir"])
    logger.info(f"Project path: {os.path.abspath(proj_dir)}")
    outputs = module_outputs(
        module,
        settings,
        localbus=bool(gen_settings.get("gen_localbus")),
        headers=bool(gen_settings["gen_header"]),
        documentation=bool(gen_settings["gen_doc"]),
    )
    top = top_level_path(module, settings)
    for relative_path, content in outputs.items():
        path = os.path.join(proj_dir, *relative_path.split("/"))
        directory, filename = os.path.split(path)
        os.makedirs(directory, exist_ok=True)
        if relative_path == top:
            _write_top(path, content, gen_settings)
        else:
            write_string_to_file(content, filename, directory, gen_settings["force_ow"])

    if gen_settings["gen_pdf"]:
        _build_pdf(module, os.path.join(proj_dir, module.name, settings.doc_dir))


def _build_pdf(module, mod_doc):
    """Run pdflatex on <module>.tex, or say that the PDF was skipped when
    pdflatex is not installed. Neither stops the run."""
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        logger.info(
            "pdflatex is not on PATH, so bust skipped the PDF. "
            f"The documentation is in {os.path.join(mod_doc, module.name + '.html')}."
        )
        return
    logger.info("Generating Documentation PDF...")
    try:
        status = subprocess.call(
            [
                pdflatex,
                "--interaction=batchmode",
                f"--output-directory={mod_doc}",
                os.path.join(mod_doc, module.name + ".tex"),
            ],
            stdout=subprocess.DEVNULL,
        )
    except OSError as e:
        logger.error(f"Could not run pdflatex ({e}). Use -p to skip the PDF.")
    else:
        if status != 0:
            log = os.path.join(mod_doc, module.name + ".log")
            logger.warning(f"pdflatex reported errors. See {log}")
