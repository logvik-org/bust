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

## Returns a binary number as a string with a given number of bits
def returnBinary(x, n):
    return ("{0:0"+str(n)+"b}").format(x)


## Test function
# Runs all functions with standard parameters
def TEST():
    pkgPath = "test/testmodule_pkg.vhd"
    regPath = "test/axi_test_module_reg_handler.vhd"
    globalPkgPath = 'test/axi_pkg.vhd'
    modPath = "test/test_module.vhd"
    wregs = [Reg('drp_address', True, 0), Reg('drp_data', True, 1),
             Reg('transceiver_settings', True, 2)]
    rregs = [Reg('transceiver_status', False, 3), Reg('run_status', False, 4),
             Reg('dec8b10b_errcnt', False, 5)]
    dataSize = 32
    addrSize = 32
    modName = 'test_module'
    
    writeRegHandler(regPath, modName, wregs, rregs, dataSize)
    writeGlobalPkg(globalPkgPath, dataSize, addrSize)
    writePkg(pkgPath, modName, wregs, rregs, dataSize, addrSize)
    writeModule(modPath, modName, wregs, rregs, dataSize, addrSize)

## Writes the axi module top-level
#
# @param filepath THe path to the file to be written
# @param modName The name of the module
# @param wregs List of rw registers
# @param rregs List of ro registers
# @param dataSize The width of data registers
# @param addrSize The width of the address vector
def writeModule(filepath, modName, wregs, rregs, dataSize, addrSize):
    ensureDirExist(filepath)
    with open(filepath, 'wt') as f:
        print('library ieee;', file=f)
        print('use ieee.std_logic_1164.all;', file=f)
        print('use ieee.numeric_std.all;', file=f)
        print('\n-- pkg files for axi bus', file=f)
        print('use work.axi_pkg.all;', file=f)
        print('use work.' + modName + '_pkg.all;', file=f)
        print('\nentity ' + modName + 'is', file=f)
        print('port (', file=f)
        print('\n-- user logic ports...', file=f)
        print('\n-- axi interface ports', file=f)
        print('areset_n : in std_logic;', file=f)
        print('axi_in : in axi_interconnect_to_slave;', file=f)
        print('axi_out : out axi_slave_to_interconnect', file=f)
        print(');', file=f)
        print('end entity ' + modName + ';\n', file=f)

        print('architecture structural of ' + modName + 'is', file=f)
        print('\n-- internal signal for readback', file=f)
        print('signal axi_out_i : axi_slave_to_interconnect;', file=f)
        print('\n-- registers', file=f)
        print('signal axi_reg_write : t_' + modName + '_reg_write;', file=f)
        print('signal axi_reg_read : t_' + modName + '_reg_read :=', file=f)

        for i, r in enumerate(rregs):
            if i == 0:
                print('(' + r.name + " => (others => '0'),", file=f)
            elif i == len(rregs)-1:
                print(r.name + " => (others => '0')", file=f)
            else:
                print(r.name + " => (others => '0'),", file=f)

        print(');', file=f)
            
        
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        print('', file=f)
        
        
    
## Writes the axi register handler file
#
# @param filepath The path to the file to be written
# @param modName The name of the module
# @param wregs List of rw registers
# @param rregs List of r registers
# @param dataSize The width of data registers
def writeRegHandler(filepath, modName, wregs, rregs, dataSize):
    # get number of bits required for slave address
    slaveAddrWidth = int(math.log2(len(wregs) + len(rregs))) + 3
    optMemAddrBits = slaveAddrWidth - 3

    ensureDirExist(filepath)
    with open(filepath, 'wt') as f:
        print('library ieee;', file=f)
        print('use ieee.std_logic_1164.all;', file=f)
        print('use ieee.numeric_std.all;', file=f)
        print('\n-- pkg files for axi bus', file=f)
        print('use work.' + modName + '_pkg.all;', file=f)
        print('entity axi_' + modName + '_reg_handler is', file=f)
        print('generic (', file=f)
        print('c_s_axi_data_width : integer := ' + str(dataSize) + ';', file=f)
        print('c_s_axi_addr_width : integer := ' + str(slaveAddrWidth), file=f)
        print(');', file=f)
        print('port (', file=f)
        print('-- Register records to and from logic', file=f)
        print('axi_reg_read : in  t_' + modName + '_reg_read;', file=f)
        print('axi_reg_write : out t_' + modName + '_reg_write;', file=f)
        print('-- AXI protocol signals', file=f)
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
        print('\n-- Internal signal for readback', file=f)
        print('signal axi_reg_write_i : t_' + modName + '_reg_write;', file=f)
        print('\n--AXI4Lite signals ', file=f)
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

        print('\n-- Module-specific design signals', file=f)
        print('-- local parameter for addressing 32 bit / 64 bit c_s_axi_data_width', file=f)
        print('-- addr_lsb is used for addressing 32/64 bit registers/memories', file=f)
        print('-- addr_lsb = 2 for 32 bits (n downto 2)', file=f)
        print('-- addr_lsb = 3 for 64 bits (n downto 3)', file=f)
        print('constant addr_lsb : integer := (c_s_axi_data_width/32)+ 1;',
              file=f)
        print('constant opt_mem_addr_bits : integer := ' + str(optMemAddrBits)
              + ';', file=f)

        print('-- Signals for user logic register space', file=f)
        print('signal slv_reg_rden : std_logic;', file=f)
        print('signal slv_reg_wren : std_logic;', file=f)
        print('signal reg_data_out : std_logic_vector(c_s_axi_data_width-1 downto 0);', file=f)
        print('signal byte_index : integer;', file=f)
        print('\nbegin', file=f)
        print('\n-- internal signal to external', file=f)
        print('axi_reg_write <= axi_reg_write_i;', file=f)
        print('\n-- i/o connections assignments', file=f)
        print('s_axi_awready <= axi_awready;', file=f)
        print('s_axi_wready <= axi_wready;', file=f)
        print('s_axi_bresp <= axi_bresp;', file=f)
        print('s_axi_bvalid <= axi_bvalid;', file=f)
        print('s_axi_arready <= axi_arready;', file=f)
        print('s_axi_rdata <= axi_rdata;', file=f)
        print('s_axi_rresp <= axi_rresp;', file=f)
        print('s_axi_rvalid <= axi_rvalid;', file=f)

        print('\n-- implement axi_awready generation', file=f)
        print('-- axi_awready is asserted for one s_axi_aclk clock cycle when both', file=f)
        print('-- s_axi_awvalid and s_axi_wvalid are asserted. axi_awready is', file=f)
        print('-- de-asserted when reset is low.', file=f)        
        print('process (s_axi_aclk)', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)
        print('''axi_awready <= '0';''', file=f)
        print('else', file=f)
        print('''if (axi_awready = '0' and s_axi_awvalid = '1' and s_axi_wvalid = '1') then''', file=f)
        print('-- slave is ready to accept write address when', file=f)
        print('-- there is a valid write address and write data', file=f)
        print('-- on the write address and data bus. this design ', file=f)
        print('-- expects no outstanding transactions. ', file=f)
        print('''axi_awready <= '1';''', file=f)
        print('else', file=f)
        print('''axi_awready <= '0';''', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;', file=f)

        print('\n-- implement axi_awaddr latching', file=f)
        print('-- this process is used to latch the address when both ', file=f)
        print('-- s_axi_awvalid and s_axi_wvalid are valid. ', file=f)
        print('process (s_axi_aclk)', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)
        print('''axi_awaddr <= (others => '0');''', file=f)
        print('else', file=f)
        print('''if (axi_awready = '0' and s_axi_awvalid = '1' and s_axi_wvalid = '1') then''', file=f)
        print('-- write address latching', file=f)
        print('axi_awaddr <= s_axi_awaddr;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;', file=f)

        print('\n-- implement axi_wready generation', file=f)
        print('-- axi_wready is asserted for one s_axi_aclk clock cycle when both', file=f)
        print('-- s_axi_awvalid and s_axi_wvalid are asserted. axi_wready is ', file=f)
        print('-- de-asserted when reset is low. ', file=f)
        print('process (s_axi_aclk)', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)
        print('''axi_wready <= '0';''', file=f)
        print('else', file=f)
        print('''if (axi_wready = '0' and s_axi_wvalid = '1' and s_axi_awvalid = '1') then''', file=f)
        print('-- slave is ready to accept write data when ', file=f)
        print('-- there is a valid write address and write data', file=f)
        print('-- on the write address and data bus. this design ', file=f)
        print('-- expects no outstanding transactions.', file=f)
        print('''axi_wready <= '1';''', file=f)
        print('else', file=f)
        print('''axi_wready <= '0';''', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;', file=f)

        print('\n-- implement memory mapped register select and write logic generation', file=f)
        print('-- the write data is accepted and written to memory mapped registers when', file=f)
        print('-- axi_awready, s_axi_wvalid, axi_wready and s_axi_wvalid are asserted. write strobes are used to', file=f)
        print('-- select byte enables of slave registers while writing.', file=f)
        print('-- these registers are cleared when reset (active low) is applied.', file=f)
        print('-- slave register write enable is asserted when valid address and data are available', file=f)
        print('-- and the slave is ready to accept the write address and write data.', file=f)
        print('slv_reg_wren <= axi_wready and s_axi_wvalid and axi_awready and s_axi_awvalid;', file=f)
        
        print('process (s_axi_aclk)', file=f)
        print('variable loc_addr : std_logic_vector(opt_mem_addr_bits downto 0);', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)

        for r in wregs:
            
            print('axi_reg_write_i.' + r.name + ''' <= (others => '0');''',
                  file=f)
            
        print('else', file=f)
        print('loc_addr := axi_awaddr(addr_lsb + opt_mem_addr_bits downto addr_lsb);', file=f)
        print('''if (slv_reg_wren = '1') then''', file=f)
        print('case loc_addr is', file=f)

        for r in wregs:
        
            print('\nwhen b"' + returnBinary(r.number, optMemAddrBits+1) + '" =>', file=f)
            print('for byte_index in 0 to (c_s_axi_data_width/8-1) loop', file=f)
            print('''if (s_axi_wstrb(byte_index) = '1') then''', file=f)
            print('-- respective byte enables are asserted as per write strobes', file=f)
            print('-- slave register' + r.name, file=f)
            print('axi_reg_write_i.' + r.name + '(byte_index*8+7 downto byte_index*8) <= s_axi_wdata(byte_index*8+7 downto byte_index*8);', file=f)
            print('end if;', file=f)
            print('end loop;', file=f)

        
        print('when others =>', file=f)

        for r in wregs:
            print('axi_reg_write_i.' + r.name + ' <= axi_reg_write_i.' + r.name + ';',
                  file=f)
        print('end case;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;\n', file=f)

        print('\n-- implement write response logic generation', file=f)
        print('-- the write response and response valid signals are asserted by the slave ', file=f)
        print('-- when axi_wready, s_axi_wvalid, axi_wready and s_axi_wvalid are asserted.  ', file=f)
        print('-- this marks the acceptance of address and indicates the status of ', file=f)
        print('-- write transaction.', file=f)
        print('process (s_axi_aclk)', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)
        print('''axi_bvalid <= '0';''', file=f)
        print('axi_bresp  <= "00";             --need to work more on the responses', file=f)
        print('else', file=f)
        print('''if (axi_awready = '1' and s_axi_awvalid = '1' and axi_wready = '1' and s_axi_wvalid = '1' and axi_bvalid = '0') then''', file=f)
        print('''axi_bvalid <= '1';''', file=f)
        print('axi_bresp  <= "00";', file=f)
        print('''elsif (s_axi_bready = '1' and axi_bvalid = '1') then  --check if bready is asserted while bvalid is high)''', file=f)
        print('''axi_bvalid <= '0';  -- (there is a possibility that bready is always asserted high)''', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;\n', file=f)

        print('\n-- implement axi_arready generation', file=f)
        print('-- axi_arready is asserted for one s_axi_aclk clock cycle when', file=f)
        print('-- s_axi_arvalid is asserted. axi_awready is ', file=f)
        print('-- de-asserted when reset (active low) is asserted. ', file=f)
        print('-- the read address is also latched when s_axi_arvalid is ', file=f)
        print('-- asserted. axi_araddr is reset to zero on reset assertion.', file=f)
        print('process (s_axi_aclk)', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)
        print('''axi_arready <= '0';''', file=f)
        print('''axi_araddr  <= (others => '1');''', file=f)
        print('else', file=f)
        print('''if (axi_arready = '0' and s_axi_arvalid = '1') then''', file=f)
        print('-- indicates that the slave has acceped the valid read address', file=f)
        print('''axi_arready <= '1';''', file=f)
        print('''-- read address latching''', file=f)
        print('axi_araddr  <= s_axi_araddr;', file=f)
        print('else', file=f)
        print('''axi_arready <= '0';''', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;\n', file=f)

        print('-- implement axi_arvalid generation', file=f)
        print('-- axi_rvalid is asserted for one s_axi_aclk clock cycle when both ', file=f)
        print('-- s_axi_arvalid and axi_arready are asserted. the slave registers ', file=f)
        print('-- data are available on the axi_rdata bus at this instance. the ', file=f)
        print('-- assertion of axi_rvalid marks the validity of read data on the ', file=f)
        print('-- bus and axi_rresp indicates the status of read transaction.axi_rvalid ', file=f)
        print('-- is deasserted on reset (active low). axi_rresp and axi_rdata are ', file=f)
        print('-- cleared to zero on reset (active low).', file=f)
        print('process (s_axi_aclk)', file=f)
        print('begin', file=f)
        print('if rising_edge(s_axi_aclk) then', file=f)
        print('''if s_axi_aresetn = '0' then''', file=f)
        print('''axi_rvalid <= '0';''', file=f)
        print('axi_rresp  <= "00";', file=f)
        print('else', file=f)
        print('''if (axi_arready = '1' and s_axi_arvalid = '1' and axi_rvalid = '0') then''', file=f)
        print('-- valid read data is available at the read data bus', file=f)
        print('''axi_rvalid <= '1';''', file=f)
        print('''axi_rresp  <= "00";           -- 'okay' response''', file=f)
        print('''elsif (axi_rvalid = '1' and s_axi_rready = '1') then''', file=f)
        print('-- read data is accepted by the master', file=f)
        print('''axi_rvalid <= '0';''', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;\n', file=f)
        
        print('\n-- implement memory mapped register select and read logic generation', file=f)
        print('-- slave register read enable is asserted when valid address is available', file=f)
        print('-- and the slave is ready to accept the read address.', file=f)
        print('slv_reg_rden <= axi_arready and s_axi_arvalid and (not axi_rvalid);\n', file=f)

        print('process (all)', file=f)
        print('variable loc_addr : std_logic_vector(opt_mem_addr_bits downto 0);', file=f)
        print('begin', file=f)
        print('-- address decoding for reading registers', file=f)
        print('loc_addr := axi_araddr(addr_lsb + opt_mem_addr_bits downto addr_lsb);', file=f)
        print('case loc_addr is', file=f)

        # Add the register lists together and sort by reg number
        regs = wregs + rregs
        regs.sort(key=lambda x: x.number, reverse=False)

        for r in regs:

            print('when b"' + returnBinary(r.number, optMemAddrBits+1) +
                  '" =>', file=f)
            if r.mode == True:
                print('reg_data_out <= axi_reg_write_i.' + r.name + ';', file=f)
            else:
                print('reg_data_out <= axi_reg_read.' + r.name + ';', file=f)

        print('when others =>', file=f)
        print('''reg_data_out <= (others => '0');''', file=f)
        print('end case;', file=f)
        print('end process;\n', file=f)

        print('-- output register or memory read data', file=f)
        print('process(s_axi_aclk) is', file=f)
        print('begin', file=f)
        print('if (rising_edge (s_axi_aclk)) then', file=f)
        print('''if (s_axi_aresetn = '0') then''', file=f)
        print('''axi_rdata <= (others => '0');''', file=f)
        print('else', file=f)
        print('''if (slv_reg_rden = '1') then''', file=f)
        print('-- when there is a valid read address (s_axi_arvalid) with ', file=f)
        print('-- acceptance of read address by the slave (axi_arready), ', file=f)
        print('-- output the read dada ', file=f)
        print('-- read address mux', file=f)
        print('axi_rdata <= reg_data_out;    -- register read data', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end if;', file=f)
        print('end process;\n', file=f)
        print('end arch_imp;', file=f)


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

