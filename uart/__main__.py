#!/usr/bin/env python3
"""uart register tool

Usage:
  uart.py FILE [-o DIR]
  uart.py -c FILE [-o DIR]
  uart.py -e FILE [-o DIR]
  uart.py --version
  uart.py -h | --help

Options:
  -o DIR         Specify output directory
  -c             Start menu-based creation of JSON file
  -e             Start menu-based editing of existing JSON file
  -h --help      HELP!
  --version      Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory

"""
from docopt import docopt
import os
import pdb
import traceback
import sys
import curses
import pkg_resources

from uart.utils import JSON_parser, write_string_to_file
from uart.module import Module
from uart.bus import Bus
from uart.editor import Editor
from uart.header import Header
from uart.documentation import Documentation

__VERSION__ = '0.5.6-dev'


def main():

    args = docopt(__doc__, help=True, version="uart " + __VERSION__)
    try:

        if args['FILE'] is not None and not args['-e'] and not args['-c']:
            JSON_file = args['FILE']

            print('Parsing file: ' + JSON_file + '...')

            try:
                json = JSON_parser(JSON_file)
                bus = Bus(json['bus'])
                mod = Module(json, bus)
                header = Header(mod)
                documentation = Documentation(mod)

            except Exception as e:
                print('An unresolvable error has occurred:')
                print(str(e))
                print('Exiting...')
                exit()

            if args['-o'] is None:
                output_dir = "output/"
            else:
                output_dir = args['-o']

            
            # Keep all files in the same directory for now, expand when handling multiple modules
            # output_dir_bus = os.path.join(output_dir, bus.bus_type)
            # output_dir_bus_hdl = os.path.join(output_dir_bus, 'hdl/')
            output_dir_mod = os.path.join(output_dir, mod.name)
            output_dir_mod_hdl = os.path.join(output_dir_mod, 'hdl/')
            output_dir_mod_header = os.path.join(output_dir_mod, 'header/')
            output_dir_mod_doc = os.path.join(output_dir_mod, 'docs/')

            try:
                print('\nCreating VHDL files...')
                write_string_to_file(bus.return_bus_pkg_VHDL(),
                                     bus.bus_type + '_pkg.vhd', output_dir_mod_hdl)
                write_string_to_file(bus.return_bus_pif_VHDL(mod),
                                     mod.name + '_' + bus.bus_type + '_pif.vhd',
                                     output_dir_mod_hdl)
                write_string_to_file(mod.return_module_pkg_VHDL(),
                                     mod.name + '_pif_pkg.vhd', output_dir_mod_hdl)
                write_string_to_file(mod.return_module_VHDL(),
                                     mod.name + '.vhd', output_dir_mod_hdl)
                print('\nCreating Header files...')
                write_string_to_file(header.return_c_header(),
                                     mod.name + '.c', output_dir_mod_header)
                write_string_to_file(header.return_python_header(),
                                     mod.name + '.py', output_dir_mod_header)
                print('\nCreating Documentation files...')
                write_string_to_file(documentation.return_tex_documentation(),
                                     mod.name + '.tex', output_dir_mod_doc)

            except Exception as e:
                print(str(e))
            return

        elif args['-c'] and args['FILE'] is not None:
            
            # Determine if file already exists, if yes ask to overwrite
            if os.path.isfile(args['FILE']):
                if input("File already exists. Overwrite? (y/N): ").upper() != 'Y':
                    exit()

            editor = Editor(False, args['FILE'])
            editor.show_menu()
            curses.endwin()

        elif args['-e'] and args['FILE'] is not None:

            # Determine if file does not exist, if yes ask to create new
            if not os.path.isfile(args['FILE']):
                if input('File does not exist. Create new file? (Y/n): ').upper() != 'N':

                    editor = Editor(False, args['FILE'])
                    editor.show_menu()
                    curses.endwin()
                else:
                    exit()
            else:
                editor = Editor(True, args['FILE'])
                editor.show_menu()
                curses.endwin()

        
    # except KeyboardInterrupt:
    #     print('\nShutdown requested. Exiting...')
    except Exception:
        traceback.print_exc(file=sys.stdout)
        exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()


###################################################################################################
# Only for debugging convenience!
###################################################################################################
dbg_args = {'--help': False,
            '--version': False,
            '-c': True,
            '-e': False,
            '-o': False,
            'FILE': 'test'}


def dbg():
    pdb.set_trace()
    main(dbg_args)
