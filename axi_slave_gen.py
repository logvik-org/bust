## @package axi_slave_gen
#  Documentation for this module.
#
#  More details.

import os
from reg import Reg

filepath = "test/output.txt"
wregs = [Reg('drp_address', True, 0), Reg('drp_data', True, 1),
         Reg('transceiver_settings', True, 2)]
rregs = [Reg('transceiver_status', False, 3), Reg('run_status', False, 4),
         Reg('dec8b10b_errcnt', False, 5)]
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
            print(r.name + ' : t_axi_data; -- reg ' + str(r.number), file=f)
        print('end record;\n', file=f)

        print('type t_' + modName + '_reg_read is record', file=f)

        for i, r in enumerate(rregs):
            print(r.name + ' : t_axi_data; -- reg ' + str(r.number), file=f)
        print('end record;\n', file=f)


def writeGlobalPkg(filepath, dataSize, addrSize):
    ensureDirExist(filepath)
