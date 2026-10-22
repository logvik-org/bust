#!/usr/bin/env python3
"""bust register tool.

Usage:
  bust FILE [-o DIR] [[[-F | -f] [-d | -p] [-i] [--replace-top] [-u] [-b] [-t] [-m]] | [-a [-F | -f]] | [--migrate [-F | -f]] | [-c | -e]]
  bust --version
  bust -h | --help

Options:
  -o DIR         Specify output directory. Overrides settings (either JSON dir, or specified project dir in JSON)
  -f             Force overwrite of existing files, except <module>.vhd, which is yours
  -F             Alias for -f, kept for compatibility
  -d             Do not generate documentation (neither LaTeX nor PDF)
  -p             Do not generate PDF from LaTeX
  -i             Do not generate the include header files (.h, .hpp & .py)
  --replace-top  Replace <module>.vhd with a fresh starter, keeping the old file as <module>.vhd.bak
  -u             Ignored with a warning, a bust 0.14 option
  -b             Ignored with a warning, a bust 0.14 option
  -t             Ignored with a warning, a bust 0.14 option
  -m             Ignored with a warning, a bust 0.14 option
  -a             Update register addresses and save JSON file (with -f, without asking)
  --migrate      Migrate a bust 0.14 JSON file and <module>.vhd (with -f, without asking)
  -e             Edit the JSON file
  -c             Create a new JSON file
  -h --help      HELP!
  --version      Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory for VHDL, header files and documentation

"""

from docopt import docopt
import sys
import shlex
import time
import logging
import logging.handlers
from typing import Any, Dict, Union

from bust.utils.json_utils import parse_json_text
from bust.validation.schema_check import check_register_map
from bust.utils.file_utils import may_overwrite
from bust.editing.document import RegisterMapDocument
from bust.editing.json_source import join_pointer
from bust.validation.config_validator import parse_number
from bust.core.module import Module
from bust.core.bus import Bus
from bust.generators.header_generator import HeaderGenerator
from bust.generators.documentation_generator import DocumentationGenerator
from bust.settings import Settings
from bust.generation import generate_output
from bust.exceptions import (
    FormatError,
    InvalidAddress,
    InvalidRegister,
    InvalidBusType,
    InvalidResetMode,
)
from bust.migrate import migrate
from bust.editor import Editor
from bust._version import __VERSION__

# bust 0.14 options that bust 1.0 accepts and ignores, so that old command lines
# and Makefiles keep working during the switch. The value is the reason the
# warning gives.
_IGNORED_0_14_OPTIONS = {
    "-u": "bust 1.0 always regenerates the top-level file",
    "-b": "bust 1.0 always writes the local-bus package",
    "-t": "bust 1.0 always writes the testbench",
    "-m": "bust 1.0 always writes the module VHDL",
}


class _DebugLog(logging.handlers.BufferingHandler):
    """Keeps every log record of the run, so that a run that fails can add
    them to debug.log. A run that succeeds leaves the file alone."""

    def __init__(self) -> None:
        super().__init__(capacity=0)

    def shouldFlush(self, record: logging.LogRecord) -> bool:
        return False

    def write(self, path: str = "debug.log") -> None:
        """Append the records after a line with the time and the command line."""
        date_format = "%a, %d %b %Y %H:%M:%S"
        formatter = logging.Formatter(
            "%(asctime)s %(name)-15s %(levelname)-8s %(message)s",
            datefmt=date_format,
        )
        with open(path, "a", encoding="utf-8") as log:
            log.write(
                f"=== {time.strftime(date_format)} bust {shlex.join(sys.argv[1:])}\n"
            )
            for record in self.buffer:
                log.write(formatter.format(record) + "\n")


def _save_addresses(json_file: str, module: Module, force: bool) -> None:
    """Give every register the next address in list order and save the file.

    Only the address values change in the text, and an address that is already
    right keeps its form.
    """
    document = RegisterMapDocument.open(json_file)
    registers = document.data["module"]["register"]
    module.update_addresses()
    operations = [
        {
            "op": "add",
            "path": join_pointer("module", "register", index, "address"),
            "value": hex(register.address),
        }
        for index, register in enumerate(module.registers)
        if "address" not in registers[index]
        or parse_number(registers[index]["address"], "address") != register.address
    ]
    document.apply(operations)
    if not document.is_modified:
        logging.getLogger(__name__).info(
            f"The addresses in {json_file} are in order already."
        )
    elif may_overwrite(json_file, force):
        document.save(json_file)


def _read_register_map(json_file: str) -> Any:
    """Read and check the register map, or stop with every problem in it.

    Each problem is printed with the file name, the line and the path to the
    value, such as ``uart.json:14: module.register[2].sw: ...``.
    """
    logger = logging.getLogger(__name__)
    try:
        # newline="" keeps the line count of a file with CR line endings.
        with open(json_file, encoding="utf-8", newline="") as fp:
            text = fp.read()
    except OSError as error:
        logger.error(f"Cannot read {json_file}: {error.strerror or error}")
        exit(1)
    except UnicodeDecodeError as error:
        logger.error(f"Cannot read {json_file}: it is not UTF-8 text ({error.reason})")
        exit(1)
    try:
        data = parse_json_text(text, json_file)
    except FormatError as error:
        logger.error(str(error))
        exit(1)
    report = check_register_map(data, text)
    for problem in report.warnings:
        logger.warning(problem.in_file(json_file))
    for problem in report.errors:
        logger.error(problem.in_file(json_file))
    if len(report.errors) > 1:
        logger.error(f"{len(report.errors)} problems in {json_file}")
    if report.errors:
        exit(1)
    return data


def main():
    args = docopt(__doc__, help=True, version="bust v" + __VERSION__)
    root = logging.getLogger("")
    root.setLevel(logging.DEBUG)
    # Messages of level INFO and above go to standard error.
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console)
    debug_log = _DebugLog()
    root.addHandler(debug_log)
    try:
        _run(args)
    except SystemExit as stop:
        if stop.code not in (None, 0):
            debug_log.write()
        raise


def _run(args):
    logger = logging.getLogger(__name__)

    for option, reason in _IGNORED_0_14_OPTIONS.items():
        if args.get(option):
            logger.warning(f"Ignoring {option}, a bust 0.14 option: {reason}.")

    try:

        if args["FILE"] is not None:
            json_file = args["FILE"]

            # Without a terminal the editor's questions get no answers, and bust
            # would exit 0 with nothing saved.
            is_terminal = sys.stdin.isatty() and sys.stdout.isatty()
            if (args["-c"] or args["-e"]) and not is_terminal:
                logger.error("The editor (-c, -e) needs an interactive terminal.")
                exit(1)

            if args["-c"] or args["-e"]:
                try:
                    start = Editor.create if args["-c"] else Editor.open
                    editor = start(json_file)
                    if editor is not None:
                        editor.run()
                except Exception as e:
                    logger.error(str(e) or type(e).__name__)
                    logger.debug("Detailed traceback:", exc_info=True)
                    exit(1)
                exit()

            # Before the normal parse, which a bust 0.14 file may not pass.
            if args["--migrate"]:
                try:
                    migrate(json_file, args["-o"], bool(args["-F"] or args["-f"]))
                except Exception as e:
                    logger.error(str(e))
                    logger.debug("Detailed traceback:", exc_info=True)
                    exit(1)
                exit()

            logger.info("Parsing file: " + json_file + "...")

            json_dict = _read_register_map(json_file)

            try:
                settings = Settings(json_file, json_dict.get("settings"))
                bus = Bus(json_dict["bus"])
                module = Module(json_dict["module"], bus, settings)
                header = HeaderGenerator(module)
                documentation = DocumentationGenerator(module)

            except (
                FormatError,
                InvalidAddress,
                InvalidRegister,
                InvalidResetMode,
                InvalidBusType,
                NotImplementedError,
            ) as e:
                logger.error(str(e))
                logger.debug("Detailed traceback:", exc_info=True)
                exit(1)

            except Exception as e:
                logger.error("An unknown error has occurred...")
                logger.error(f"{type(e).__name__}: {e}")
                logger.debug("Detailed traceback:", exc_info=True)
                exit(1)

            # File generation settings
            gs: Dict[str, Union[bool, str]] = {}

            if args["-o"] is None:
                gs["dir"] = settings.project_path
            else:
                gs["dir"] = args["-o"]

            # Check if force overwrite is set
            gs["force_ow"] = bool(args["-F"] or args["-f"])
            gs["replace_top"] = bool(args["--replace-top"])

            gs["gen_doc"] = True
            gs["gen_pdf"] = True
            if args["-d"]:
                gs["gen_doc"] = False
                gs["gen_pdf"] = False
            elif args["-p"]:
                gs["gen_pdf"] = False

            gs["gen_header"] = True
            if args["-i"]:
                gs["gen_header"] = False

            gs["gen_localbus"] = True

            if args["-a"]:
                try:
                    _save_addresses(json_file, module, bool(gs["force_ow"]))
                except Exception as e:
                    logger.error(f"Saving {json_file} failed: {e}")
                    exit(1)
            else:
                try:
                    generate_output(settings, bus, module, header, documentation, gs)
                except Exception as e:
                    logger.error("An error occurred during output generation...")
                    logger.error(f"{type(e).__name__}: {e}")
                    logger.debug("Detailed traceback:", exc_info=True)
                    exit(1)

    except Exception:
        logger.exception("An unresolvable error has occurred...")
        logger.debug("Detailed traceback:", exc_info=True)
        exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
