#!/usr/bin/env python3
"""art - AXI register tool

Usage:
  art.py FILE [-o DIR]
  art.py -c FILE [-o DIR]
  art.py -e FILE [-o DIR]
  art.py --version
  art.py -h | --help

Options:
  -o DIR         Specify output directory
  -c             Start menu-based creation of JSON file
  -e             Edit existing JSON file
  -h --help      HELP!
  --version      Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory

"""
from docopt import docopt
from utils import jsonParser
from utils import writeStringToFile
from module import Module
from module import Bus
from editor import Editor
import os
import pdb


def main(args):

    if args['FILE'] is not None and not args['-e'] and not args['-c']:
        jsonFile = args['FILE']

        print('Parsing file: ' + jsonFile + '...')

        json = jsonParser(jsonFile)

        # AXI BUS FOR NOW
        axi = {'bus_type': 'axi', 'data_width': 32, 'addr_width': 32}
        bus = Bus(axi)

        mod = Module(json, bus)

        if args['-o'] is None:
            outputDir = "output/"
        else:
            outputDir = args['-o']

        print('Creating VHDL files...')
        # Keep all files in the same directory for now, expand when handling multiple modules
        # outputDirBus = os.path.join(outputDir, bus.busType)
        # outputDirBusHDL = os.path.join(outputDirBus, 'hdl/')
        outputDirMod = os.path.join(outputDir, mod.name)
        outputDirModHDL = os.path.join(outputDirMod, 'hdl/')

        try:
            writeStringToFile(bus.returnBusPkgVHDL(),
                              bus.busType + '_pkg.vhd', outputDirModHDL)

            writeStringToFile(mod.returnRegisterPIFVHDL(),
                              mod.name + '_axi_pif.vhd', outputDirModHDL)
            writeStringToFile(mod.returnModulePkgVHDL(),
                              mod.name + '_pkg.vhd', outputDirModHDL)
            writeStringToFile(mod.returnModuleVHDL(),
                              mod.name + '.vhd', outputDirModHDL)

        except Exception as e:
            print(str(e))
        return

    elif args['-c'] and args['FILE'] is not None:
        editor = Editor(False, args['FILE'])
        editor.showMenu()
        print("This feature is not yet implemented. Planned for art version 0.2")
        return

    elif args['-e'] and args['FILE'] is not None:
        editor = Editor(True, args['FILE'])
        editor.showMenu()
        print("This feature is not yet implemented. Planned for art version 0.2")
        return


if __name__ == '__main__':

    args = docopt(__doc__, help=True, version='art version 0.1.1')
    main(args)

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
