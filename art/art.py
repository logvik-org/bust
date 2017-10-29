#!/usr/bin/env python
"""art - axi register tool

Usage:
  art.py FILE [-o DIR]
  art.py -c [-o DIR]
  art.py --version
  art.py -h | --help

Options:
  -o DIR         Specify output directory
  -c             Start menu-based creation of JSON file
  -h --help      HELP!
  --version   Show version info

Arguments:
  FILE         Module configuration file, JSON format
  DIR          Output directory

"""
from docopt import docopt
from utils import jsonParser
from utils import writeStringToFile
from exceptions import *
from module import Module

if __name__ == '__main__':
    arguments = docopt(__doc__, version='art version 0.1')

    if arguments['FILE'] != None:
        jsonFile = arguments['FILE']

        
            
        print('Parsing file: ' + jsonFile + '...')

        json = jsonParser(jsonFile)
        mod = Module(json)

        if arguments['-o'] == None:
            outputDir = mod.name + "/"
        else:
            outputDir = arguments['DIR']

        print('Creating VHDL files...')
        outputDirHDL = outputDir + 'hdl/'
        writeStringToFile(mod.returnRegisterPIFVHDL(), mod.name + '_axi_pif.vhd', outputDirHDL)
        writeStringToFile(mod.returnBusPkgVHDL(), 'axi_pkg.vhd', outputDirHDL)
        writeStringToFile(mod.returnModulePkgVHDL(), mod.name + '_pkg.vhd', outputDirHDL)
        writeStringToFile(mod.returnModuleVHDL(), mod.name + '.vhd', outputDirHDL)
        
        
