#!/usr/bin/env python
"""art - AXI register tool

Usage:
  art.py FILE [-o DIR]
  art.py -c [-o DIR]
  art.py --version
  art.py -h | --help

Options:
  -o DIR         Specify output directory
  -c             Start menu-based creation of JSON file
  -h --help      HELP!
  --version      Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory

"""
from docopt import docopt
from utils import jsonParser
from utils import writeStringToFile
from exceptions import *
from module import Module
from module import Bus
import os

if __name__ == '__main__':
    arguments = docopt(__doc__, version='art version 0.1')

    if arguments['FILE'] != None:
        jsonFile = arguments['FILE']

        print('Parsing file: ' + jsonFile + '...')

        json = jsonParser(jsonFile)

        # AXI BUS FOR NOW
        axi = {'bus_type': 'axi', 'data_width': 32, 'addr_width': 32}
        bus = Bus(axi)

        mod = Module(json, bus.busType)

        if arguments['-o'] == None:
            outputDir = "output/"
        else:
            outputDir = arguments['-o']

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
