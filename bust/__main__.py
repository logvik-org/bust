#!/usr/bin/env python3
"""bust register tool

Usage:
  bust.py FILE [-o DIR] [-F | -f] [-u] [-d | -p] [-b] [-t] [-i] [-m] [-a]
  bust.py --version
  bust.py -h | --help

Options:
  -o DIR         Specify output directory. Overrides settings (either JSON dir, or specified project dir in JSON)
  -f             Force overwrite of existing files except module top level VHDL file
  -F             Force overwrite of ALL existing files
  -u             Try to update top-level file - MAY OVERWRITE USER EDITS!
  -d             Do not generate documentation (neither LaTeX nor PDF)
  -p             Do not generate PDF from LaTeX
  -b             Do not generate the bus VHDL package file
  -t             Do not generate the testbench VHDL file and the simulation scripts
  -i             Do not generate the include header files (.h, .hpp & .py)
  -m             Do not generate the module VHDL files
  -a             Update register addresses and save JSON file
  -h --help      HELP!
  --version      Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory for VHDL, header files and documentation

"""
from docopt import docopt
import os
import subprocess
import pdb
import traceback
import sys
import curses
import pkg_resources
import logging

from bust.utils import json_parser, write_string_to_file, update_module_top_level
from bust.module import Module
from bust.bus import Bus
from bust.editor import Editor
from bust.header import Header
from bust.documentation import Documentation
from bust.settings import Settings
from bust.testbench import Testbench
from bust.generation import generate_output

__VERSION__ = '0.7.0-dev'


def main():
    args = docopt(__doc__, help=True, version="bust " + __VERSION__)
    logging.basicConfig(filename='debug.log', filemode='w', datefmt='%a, %d %b %Y %H:%M:%S',
                        format='%(asctime)s %(name)-15s %(levelname)-8s %(message)s', level=logging.DEBUG)
    # Define a handler which writes INFO or higher to sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # Define a simpler format for sys.stderr
    formatter = logging.Formatter('%(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)
    logger = logging.getLogger(__name__)

    if args['-a']:
        # TODO
        raise NotImplementedError("The address update feature is not yet implemented")

    try:

        if args['FILE'] is not None:
            json_file = args['FILE']

            logger.info('Parsing file: ' + json_file + '...')

            try:
                json_dict = json_parser(json_file)
                settings = Settings(json_file, json_dict['settings'])
                bus = Bus(json_dict['bus'])
                module = Module(json_dict['module'], bus, settings)
                header = Header(module)
                documentation = Documentation(module)
                testbench = Testbench(module, bus, settings)

            except Exception as e:
                logger.exception('An unresolvable error has occurred...')
                exit(1)

            # File generation settings
            gs = {}

            if args['-o'] is None:
                gs['dir'] = settings.project_path
            else:
                gs['dir'] = args['-o']

            # Check if force overwrite is set
            gs['force_ow'] = False
            gs['force_ow_top'] = False
            if args['-F']:
                gs['force_ow'] = True
                gs['force_ow_top'] = True
            elif args['-f']:
                gs['force_ow'] = True

            # Check if top-level are to be updated
            gs['update_top'] = False
            if args['-u']:
                gs['update_top'] = True
                gs['force_ow_top'] = True

            gs['gen_bus'] = True
            if args['-b']:
                gs['gen_bus'] = False

            gs['gen_doc'] = True
            gs['gen_pdf'] = True
            if args['-d']:
                gs['gen_doc'] = False
                gs['gen_pdf'] = False
            elif args['-p']:
                gs['gen_pdf'] = False

            gs['gen_tb'] = True
            if args['-t']:
                gs['gen_tb'] = False

            gs['gen_header'] = True
            if args['-i']:
                gs['gen_header'] = False

            gs['gen_mod'] = True
            if args['-m']:
                gs['gen_mod'] = False

            generate_output(settings, bus, module, header, documentation, testbench, gs)

            # # Keep all files in the same directory for now, expand when handling multiple modules
            # # output_dir_bus = os.path.join(output_dir, bus.bus_type)
            # # output_dir_bus_hdl = os.path.join(output_dir_bus, 'hdl/')
            # if args['-d']:
            #     output_dir_mod = output_dir
            # else:
            #     output_dir_mod = os.path.join(output_dir, mod.name)
            #
            # output_dir_mod_hdl = os.path.join(output_dir_mod, 'hdl/')
            # output_dir_mod_header = os.path.join(output_dir_mod, 'header/')
            # output_dir_mod_doc = os.path.join(output_dir_mod, 'docs/')
            #
            # try:
            #     print('\nCreating VHDL files...')
            #
            #     if gen_bus_package:
            #         write_string_to_file(bus.return_bus_pkg_VHDL(),
            #                              bus.bus_type + '_pkg.vhd', output_dir_mod_hdl, force_overwrite)
            #
            #     write_string_to_file(bus.return_bus_pif_VHDL(mod),
            #                          mod.name + '_' + bus.bus_type + '_pif.vhd',
            #                          output_dir_mod_hdl, force_overwrite)
            #     write_string_to_file(mod.return_module_pkg_VHDL(),
            #                          mod.name + '_pif_pkg.vhd', output_dir_mod_hdl, force_overwrite)
            #
            #     if update_top_level:
            #         try:
            #             new_top_level = update_module_top_level(os.path.join(output_dir_mod_hdl,
            #                                                                  mod.name + '.vhd'),
            #                                                     mod.return_module_VHDL())
            #             write_string_to_file(new_top_level, mod.name + '.vhd', output_dir_mod_hdl,
            #                                  force_overwrite_top)
            #         except Exception as e:
            #             print(e)
            #             logger.exception('')
            #
            #     else:
            #         write_string_to_file(mod.return_module_VHDL(), mod.name + '.vhd', output_dir_mod_hdl,
            #                              force_overwrite_top)
            #
            #     print('\nCreating Header files...')
            #     write_string_to_file(header.return_c_header(),
            #                          mod.name + '.h', output_dir_mod_header, force_overwrite)
            #     write_string_to_file(header.return_cpp_header(),
            #                          mod.name + '.hpp', output_dir_mod_header, force_overwrite)
            #     write_string_to_file(header.return_python_header(),
            #                          mod.name + '.py', output_dir_mod_header, force_overwrite)
            #     print('\nCreating Documentation files...')
            #     write_string_to_file(documentation.return_tex_documentation(),
            #                          mod.name + '.tex', output_dir_mod_doc, force_overwrite)


            # # Try to generate PDF docs?
            # if args['-p']:
            #     try:
            #         subprocess.call(["pdflatex", "--output-directory=" + output_dir_mod_doc,
            #                          os.path.join(output_dir_mod_doc, mod.name + '.tex')],
            #                         stdout=open(os.devnull, 'wb'))
            #         if os.path.isfile(os.path.join(output_dir_mod_doc, mod.name + '.pdf')):
            #             print("PDF docs successfully generated...")
            #     except Exception as e:
            #         print("PDF-generation failed...")
            #         logger.exception("PDF-generation failed...")


        elif args['-c'] and args['FILE'] is not None:
            raise NotImplementedError("The menu system is removed")
            # # Determine if file already exists, if yes ask to overwrite
            # if os.path.isfile(args['FILE']):
            #     if input("File already exists. Overwrite? (y/N): ").upper() != 'Y':
            #         exit()
            #
            # editor = Editor(False, args['FILE'])
            # editor.show_menu()
            # curses.endwin()

        elif args['-e'] and args['FILE'] is not None:
            raise NotImplementedError("The menu system is removed")
            # # Determine if file does not exist, if yes ask to create new
            # if not os.path.isfile(args['FILE']):
            #     if input('File does not exist. Create new file? (Y/n): ').upper() != 'N':
            #
            #         editor = Editor(False, args['FILE'])
            #         editor.show_menu()
            #         curses.endwin()
            #     else:
            #         exit()
            # else:
            #     print(args['FILE'])
            #     editor = Editor(True, args['FILE'])
            #     editor.show_menu()
            #     curses.endwin()

    except Exception:
        logger.exception('An unresolvable error has occurred...')
        exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()