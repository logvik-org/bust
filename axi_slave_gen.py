## @package axi_slave_gen
#  Documentation for this module.
#
#  More details.

import os
import math
from reg import Reg

pkgPath = "test/testmodule_pkg.vhd"
regPath = "test/axi_test_module_reg_handler.vhd"
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

## Writes the axi register handler file for each module
#
# @param filepath The path to the file to be written
# @param modName The name of the module
# @param wregs List of rw registers
# @param rregs List of r registers
# @param dataSize The width of data registers
# @param addrSize The width of the address vector
def writeRegHandler(filepath, modName, wregs, rregs, dataSize):
    # get number of bits required for slave address
    slaveAddrWidth = int(math.log2(len(wregs) + len(rregs))) + 3
    optMemAddrBits = slaveAddrWidth - 3

    ensureDirExist(filepath)
    with open(filepath, 'wt') as f:
        print('library ieee;', file=f)
        print('use ieee.std_logic_1164.all;', file=f)
        print('use ieee.numeric_std.all;', file=f)
        print('use work.' + modName + '_pkg.all;', file=f)
        print('entity axi_' + modName + '_reg_handler is', file=f)
        print('generic (', file=f)
        print('c_s_axi_data_width : integer := ' + str(dataSize) + ';', file=f)
        print('c_s_axi_addr_width : integer := ' + str(slaveAddrWidth), file=f)
        print(');', file=f)
        print('port (', file=f)
        print('axi_reg_read : in  t_' + modName + '_reg_read;', file=f)
        print('axi_reg_write : out t_' + modName + '_reg_write;', file=f)
        print('s_axi_aclk : in std_logic;', file=f)
        print('s_axi_aresetn : in std_logic;', file=f)
        print('s_axi_awaddr : in std_logic_vector(c_s_axi_addr_width-1 downto 0);', file=f)
        print('s_axi_awprot : in std_logic_vector(2 downto 0);', file=f)
        print('s_axi_awvalid : in std_logic;', file=f)
        print('s_axi_awready : out std_logic;', file=f)
        print('s_axi_wdata : in std_logic_vector(c_s_axi_data_width-1 downto 0);', file=f)
        print('s_axi_wstrb : in std_logic_vector((c_s_axi_data_width/8)-1 downto 0);', file=f)
        print('s_axi_wvalid : in std_logic;', file=f)
        print('s_axi_wready : out std_logic;', file=f)
        print('s_axi_bresp: out std_logic_vector(1 downto 0);', file=f)
        print('s_axi_bvalid : out std_logic;', file=f)
        print('s_axi_bready : in std_logic;', file=f)
        print('s_axi_araddr : in std_logic_vector(c_s_axi_addr_width-1 downto 0);', file=f)
        print('s_axi_arprot : in std_logic_vector(2 downto 0);', file=f)
        print('s_axi_arvalid : in std_logic;', file=f)
        print('s_axi_arready : out std_logic;', file=f)
        print('s_axi_rdata : out std_logic_vector(c_s_axi_data_width-1 downto 0);', file=f)
        print('s_axi_rresp : out std_logic_vector(1 downto 0);', file=f)
        print('s_axi_rvalid : out std_logic;', file=f)
        print('s_axi_rready : in  std_logic', file=f)
        print(');', file=f)
        print('end axi_' + modName + '_reg_handler;\n', file=f)
        print('architecture arch_imp of axi_' + modName + '_reg_handler is', file=f)
        print('signal axi_reg_write_i : t_alpide_data_reg_write;', file=f)
        print('signal axi_awaddr : std_logic_vector(c_s_axi_addr_width-1 downto 0);', file=f)
        print('signal axi_awready : std_logic;', file=f)
        print('signal axi_wready : std_logic;', file=f)
        print('signal axi_bresp : std_logic_vector(1 downto 0);', file=f)
        print('signal axi_bvalid : std_logic;', file=f)
        print('signal axi_araddr : std_logic_vector(c_s_axi_addr_width-1 downto 0);', file=f)
        print('signal axi_arready : std_logic;', file=f)
        print('signal axi_rdata : std_logic_vector(c_s_axi_data_width-1 downto 0);', file=f)
        print('signal axi_rresp : std_logic_vector(1 downto 0);', file=f)
        print('signal axi_rvalid : std_logic;', file=f)
        print('constant addr_lsb : integer := (c_s_axi_data_width/32)+ 1;',
              file=f)
        print('constant opt_mem_addr_bits : integer := ' + str(optMemAddrBits)
              + ';', file=f)
        print('signal slv_reg_rden : std_logic;', file=f)
        print('signal slv_reg_wren : std_logic;', file=f)
        print('signal reg_data_out : std_logic_vector(c_s_axi_data_width-1 downto 0);', file=f)
        print('signal byte_index : integer;', file=f)
        print('\nbegin', file=f)
        print('axi_reg_write <= axi_reg_write_i;', file=f)
        print('s_axi_awready <= axi_awready;', file=f)
        print('s_axi_wready <= axi_wready;', file=f)
        print('s_axi_bresp <= axi_bresp;', file=f)
        print('s_axi_bvalid <= axi_bvalid;', file=f)
        print('s_axi_arready <= axi_arready;', file=f)
        print('s_axi_rdata <= axi_rdata;', file=f)
        print('s_axi_rresp <= axi_rresp;', file=f)
        print('s_axi_rvalid <= axi_rvalid;', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        
        


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

## Write the global pkg file

# Defines the subtypes of axi data and address
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

