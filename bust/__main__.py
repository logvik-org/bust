#!/usr/bin/env python3
"""bust register tool.

Usage:
  bust FILE [-o DIR] [[[-F | -f] [-d | -p] [-i] [-u] [-b] [-t] [-m]] | [-a [-F | -f]] | [-c | -e]]
  bust --version
  bust -h | --help

Options:
  -o DIR         Specify output directory. Overrides settings (either JSON dir, or specified project dir in JSON)
  -f             Force overwrite of existing files (the top-level wrapper is a fixed, regenerated file)
  -F             Alias for -f, kept for compatibility
  -d             Do not generate documentation (neither LaTeX nor PDF)
  -p             Do not generate PDF from LaTeX
  -i             Do not generate the include header files (.h, .hpp & .py)
  -u             Ignored with a warning, a bust 0.14 option
  -b             Ignored with a warning, a bust 0.14 option
  -t             Ignored with a warning, a bust 0.14 option
  -m             Ignored with a warning, a bust 0.14 option
  -a             Update register addresses and save JSON file (with -f, without asking)
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
import logging
import logging.handlers
from typing import Dict, Union

from bust.utils.json_utils import json_parser
from bust.validation.config_validator import warn_unknown_keys
from bust.utils.file_utils import write_string_to_file
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
    """Keeps every log record of the run, so that a run that fails can write
    them to debug.log. A run that succeeds leaves no file behind."""

    def __init__(self) -> None:
        super().__init__(capacity=0)

    def shouldFlush(self, record: logging.LogRecord) -> bool:
        return False

    def write(self, path: str = "debug.log") -> None:
        handler = logging.FileHandler(path, mode="w")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(name)-15s %(levelname)-8s %(message)s",
                datefmt="%a, %d %b %Y %H:%M:%S",
            )
        )
        for record in self.buffer:
            handler.handle(record)
        handler.close()


def main():
    args = docopt(__doc__, help=True, version="bust " + __VERSION__)
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

            # The editor's curses menus fail in a background thread without a
            # terminal, which would leave bust exiting 0 with nothing saved.
            is_terminal = sys.stdin.isatty() and sys.stdout.isatty()
            if (args["-c"] or args["-e"]) and not is_terminal:
                logger.error("The editor (-c, -e) needs an interactive terminal.")
                exit(1)

            if args["-c"] and json_file is not None:
                try:
                    e = Editor(False, json_file)
                    e.show_menu()
                except Exception as e:
                    logger.error("Failed to create new JSON file: " + json_file)
                    logger.error(f"{type(e).__name__}: {e}")
                    logger.debug("Detailed traceback:", exc_info=True)
                    exit(1)
                exit()

            if args["-e"] and json_file is not None:
                try:
                    editor = Editor(True, json_file)
                    editor.show_menu()
                except Exception as e:
                    logger.error("Failed to open editor for " + json_file)
                    logger.error(f"{type(e).__name__}: {e}")
                    logger.debug("Detailed traceback:", exc_info=True)
                    exit(1)
                exit()

            logger.info("Parsing file: " + json_file + "...")

            try:
                json_dict = json_parser(json_file)
                warn_unknown_keys(json_dict, ("settings", "bus", "module"), "the file")
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
                module.update_addresses()
                json = module.to_json(True)
                try:
                    write_string_to_file(json, json_file, ".", bool(gs["force_ow"]))
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
