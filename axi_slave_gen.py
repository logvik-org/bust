## @package axi_slave_gen
#  Documentation for this module.
#
#  More details.

import os


filepath = "test/output.txt"
wregs = ['drp_address', 'drp_data', 'transceiver_settings']
rregs = ['transceiver_status', 'run_status', 'dec8b10b_errcnt']
dataSize = 32
addrSize = 32


## Creates a directory if it does not already exist.
def ensureDirExist(filepath):
    dir = os.path.dirname(filepath)
    if not os.path.exists(dir):
        os.makedirs(dir)


def writeJibberish(filepath):
    ensureDirExist(filepath)
    with open(filepath, 'wt') as f:
        f.write('Jibberish')
        f.write('Jobberish')


## Writes the pkg-file for each module.
#
# Takes the filepath, the module name and two lists of registers as parameters
# as well as the size of the register data and address vectors
def writePkg(filepath, modName, wregs, rregs, dataSize, addrSize):

    ensureDirExist(filepath)
    with open(filepath, 'wt') as f:
        print('type t_' + modName + '_reg_write is record', file=f)

        for i, r in enumerate(wregs):
            print(r + ' : t_axi_data;', file=f)
        print('end record;\n', file=f)

        print('type t_' + modName + '_reg_read is record', file=f)

        for i, r in enumerate(rregs):
            print(r + ' : t_axi_data;', file=f)
        print('end record;\n', file=f)


def writeGlobalPkg(filepath, dataSize, addrSize):
    ensureDirExist(filepath)
    
