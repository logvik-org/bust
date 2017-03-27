## @package axi_slave_gen
#  Documentation for this module.
#
#  More details.

import os
from reg import Reg

pkgPath = "test/pkg.vhd"
globalPkgPath = 'test/axi_pkg.vhd'
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
        print('library ieee;', file=f)
        print('use ieee.std_logic_1164.all;', file=f)
        print('use ieee.numeric_std.all;\n', file=f)
        print('use work.axi_pkg.all;\n', file=f)
        print('package ' + modName + '_pkg is\n', file=f)
        print('type t_' + modName + '_reg_write is record', file=f)

        for i, r in enumerate(wregs):
            print(r.name + ' : t_axi_data; -- reg ' + str(r.number), file=f)
        print('end record;\n', file=f)

        print('type t_' + modName + '_reg_read is record', file=f)

        for i, r in enumerate(rregs):
            print(r.name + ' : t_axi_data; -- reg ' + str(r.number), file=f)
        print('end record;\n', file=f)

        print('type t_address is record', file=f)

        for r in wregs:
            print(r.name + ' : t_axi_addr;', file=f)

        for r in rregs:
            print(r.name + ' : t_axi_addr;', file=f)
        print('end record t_address;\n', file=f)

        print('constant reg_num : t_address :=(', file=f)

        for r in wregs:
            print(r.name + ' => ' + str(addrSize) + 'x"' +
                  str(r.number) + '",', file=f)

        for r in rregs[:-1]:
            print(r.name + ' => ' + str(addrSize) + 'x"' +
                  str(r.number) + '",', file=f)
        else:
            print(rregs[-1].name + ' => ' + str(addrSize) + 'x"' +
                  str(rregs[-1].number) + '"', file=f)

        print(');\n', file=f)

        print('end package ' + modName + '_pkg;', file=f)


def writeGlobalPkg(filepath, dataSize, addrSize):

    ensureDirExist(filepath)
    with open(filepath, 'wt') as f:
        print('library ieee;', file=f)
        print('use ieee.std_logic_1164.all;\n', file=f)

        print('package axi_pkg is', file=f)
        print('constant c_axi_data_width : natural := ' +
              str(dataSize) + ';', file=f)
        print('constant c_axi_addr_width : natural := ' +
              str(addrSize) + ';', file=f)
        print('subtype t_axi_data is std_logic_vector(c_axi_data_width-1 downto 0);', file=f)
        print('subtype t_axi_addr is std_logic_vector(c_axi_addr_width-1 downto 0);', file=f)
        print('\nend axi_pkg;', file=f)

