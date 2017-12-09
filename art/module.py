from utils import indentString
from utils import jsonParser
# from utils import compareJSON
# from utils import jsonToString
from exceptions import InvalidAddress
from exceptions import InvalidRegister
from exceptions import UndefinedEntryType
from exceptions import UndefinedRegisterType

from register import Register

import json
from collections import OrderedDict


def test():
    #try:
        a = jsonParser('module2.json')
        axi = {'bus_type': 'axi', 'data_width': 32, 'addr_width': 32}
        bus = Bus(axi)
        mod = Module(a, bus)
        # print(mod)
        # print(mod.returnModulePkgVHDL())

        # print(mod.printJSON(False))
        # print(mod.printJSON(True))
        # print(jsonToString())
        # print(compareJSON(jsonToString(), mod.printJSON(False), True))
        # print(mod.returnRegisterPIFVHDL())
        # print(mod.returnBusPkgVHDL())
        # print(mod.returnModuleVHDL())

    #except Exception as e:
        #print(str(e))


class Bus(object):
    """! @brief Managing bus information

    """

    def __init__(self, bus):
        self.busType = bus['bus_type']
        self.busDataWitdh = bus['data_width']
        self.busAddrWitdh = bus['addr_width']

    def returnBusPkgVHDL(self):
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += '\n'

        s += 'package ' + self.busType + '_pkg is\n'
        s += '\n\n'

        dataWidthConstant = 'C_' + self.busType.upper() + '_DATA_WIDTH'
        addrWidthConstant = 'C_' + self.busType.upper() + '_ADDR_WIDTH'
        dataSubType = 't_' + self.busType + '_data'
        addrSubType = 't_' + self.busType + '_addr'

        par = ''
        par += 'constant ' + dataWidthConstant
        par += ' : natural := ' + str(self.busDataWitdh) + ';\n'
        par += 'constant ' + addrWidthConstant
        par += ' : natural := ' + str(self.busAddrWitdh) + ';\n'
        par += '\n'
        par += 'subtype ' + dataSubType + ' is std_logic_vector('
        par += dataWidthConstant + '-1 downto 0);\n'
        par += 'subtype ' + addrSubType + ' is std_logic_vector('
        par += addrWidthConstant + '-1 downto 0);\n'
        par += '\n'
        s += indentString(par)

        s += indentString('type t_' + self.busType)
        s += '_interconnect_to_slave is record\n'
        par = ''
        par += 'araddr  : ' + addrSubType + ';\n'
        par += 'arprot  : std_logic_vector(2 downto 0);\n'
        par += 'arvalid : std_logic;\n'
        par += 'awaddr  : ' + addrSubType + ';\n'
        par += 'awprot  : std_logic_vector(2 downto 0);\n'
        par += 'awvalid : std_logic;\n'
        par += 'bready  : std_logic;\n'
        par += 'rready  : std_logic;\n'
        par += 'wdata   : ' + dataSubType + ';\n'
        par += 'wstrb   : std_logic_vector((' + dataWidthConstant
        par += '/8)-1 downto 0);\n'
        par += 'wvalid  : std_logic;\n'
        s += indentString(par, 2)
        s += indentString('end record;\n')
        s += '\n'

        s += indentString('type t_' + self.busType)
        s += '_slave_to_interconnect is record\n'
        par = ''
        par += 'arready : std_logic;\n'
        par += 'awready : std_logic;\n'
        par += 'bresp   : std_logic_vector(1 downto 0);\n'
        par += 'bvalid  : std_logic;\n'
        par += 'rdata   : ' + dataSubType + ';\n'
        par += 'rresp   : std_logic_vector(1 downto 0);\n'
        par += 'rvalid  : std_logic;\n'
        par += 'wready  : std_logic;\n'
        s += indentString(par, 2)
        s += indentString('end record;\n')
        s += '\n'

        s += 'end ' + self.busType + '_pkg;'

        return s


class Module:
    """! @brief Managing module information


    """

    def __init__(self, mod, bus):
        """! @brief
        """
        self.busType = bus.busType
        self.busAddrWitdh = bus.busAddrWitdh
        self.busDataWitdh = bus.busDataWitdh
        self.registers = []
        self.addresses = []
        self.name = mod['name']
        self.addrWidth = mod['addr_width']
        self.dataWidth = mod['data_width']
        self.description = mod['description']
        for reg in mod['register']:
            self.addRegister(reg)

    def addRegister(self, reg):
        if self.registerValid(reg):
            if "address" in reg:
                addr = int(reg['address'], self.addrWidth)
                if self.isAddressFree(addr):
                    self.isAddressOutOfRange(addr)
                    self.addresses.append(addr)
                    self.registers.append(Register(reg, addr, self.dataWidth))
                else:
                    raise InvalidAddress(reg['name'], addr)
            else:
                addr = self.getNextAddress()
                self.addresses.append(addr)
                self.registers.append(Register(reg, addr, self.dataWidth))
        else:
            raise InvalidRegister(reg)

    def returnRegisterPIFVHDL(self):

        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += 'use work.' + self.name + '_pkg.all;\n\n'
        s += 'entity ' + self.name + '_' + self.busType + '_pif is\n\n'

        s += indentString('port (')

        par = ''
        par += '\n-- register record signals\n'
        par += 'axi_ro_regs : in  t_' + self.name + '_ro_regs := '
        par += 'c_' + self.name + '_ro_regs;\n'
        par += 'axi_rw_regs : out t_' + self.name + '_rw_regs := '
        par += 'c_' + self.name + '_rw_regs;\n'
        par += '\n'
        par += '-- bus signals\n'
        par += 'clk         : in  std_logic;\n'
        par += 'areset_n    : in  std_logic;\n'
        par += 'awaddr      : in  t_' + self.name + '_addr;\n'
        par += 'awvalid     : in  std_logic;\n'
        par += 'awready     : out std_logic;\n'
        par += 'wdata       : in  t_' + self.name + '_data;\n'
        par += 'wvalid      : in  std_logic;\n'
        par += 'wready      : out std_logic;\n'
        par += 'bresp       : out std_logic_vector(1 downto 0);\n'
        par += 'bvalid      : out std_logic;\n'
        par += 'bready      : in  std_logic;\n'
        par += 'araddr      : in  t_' + self.name + '_addr;\n'
        par += 'arvalid     : in  std_logic;\n'
        par += 'arready     : out std_logic;\n'
        par += 'rdata       : out t_' + self.name + '_data;\n'
        par += 'rresp       : out std_logic_vector(1 downto 0);\n'
        par += 'rvalid      : out std_logic;\n'
        par += 'rready      : in  std_logic\n'
        par += ');\n'
        s += indentString(par, 2)

        s += 'end ' + self.name + '_axi_pif;\n\n'

        s += 'architecture behavior of ' + self.name + '_axi_pif is\n\n'

        par = ''
        par += '-- internal signal for readback' + '\n'
        par += 'signal axi_rw_regs_i : t_'
        par += self.name + '_rw_regs := c_' + self.name + '_rw_regs;\n\n'

        par += '-- internal bus signals for readback\n'
        par += 'signal awaddr_i      : t_' + self.name + '_addr;\n'
        par += 'signal awready_i     : std_logic;\n'
        par += 'signal wready_i      : std_logic;\n'
        par += 'signal bresp_i       : std_logic_vector(1 downto 0);\n'
        par += 'signal bvalid_i      : std_logic;\n'
        par += 'signal araddr_i      : t_' + self.name + '_addr;\n'
        par += 'signal arready_i     : std_logic;\n'
        par += 'signal rdata_i       : t_' + self.name + '_data;\n'
        par += 'signal rresp_i       : std_logic_vector(1 downto 0);\n'
        par += 'signal rvalid_i      : std_logic;\n\n'

        par += 'signal slv_reg_rden : std_logic;\n'
        par += 'signal slv_reg_wren : std_logic;\n'
        par += 'signal reg_data_out : t_' + self.name + '_data;\n'
        par += '-- signal byte_index   : integer' + '; -- unused\n\n'
        s += indentString(par)

        s += 'begin\n\n'
        s += indentString('axi_rw_regs <= axi_rw_regs_i') + ';\n'
        s += '\n'

        par = ''
        par += 'awready <= awready_i;\n'
        par += 'wready  <= wready_i;\n'
        par += 'bresp   <= bresp_i;\n'
        par += 'bvalid  <= bvalid_i;\n'
        par += 'arready <= arready_i;\n'
        par += 'rdata   <= rdata_i;\n'
        par += 'rresp   <= rresp_i;\n'
        par += 'rvalid  <= rvalid_i;\n'
        par += '\n'

        s += indentString(par)

        s += indentString('p_awready : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("awready_i <= '0';\n", 4)
        s += indentString("elsif (awready_i = '0' and awvalid = '1' ", 3)
        s += "and wvalid = '1') then\n"
        s += indentString("awready_i <= '1';\n", 4)
        s += indentString('else\n', 3)
        s += indentString("awready_i <= '0';\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_awready;\n')
        s += '\n'

        s += indentString('p_awaddr : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("awaddr_i <= (others => '0');\n", 4)
        s += indentString("elsif (awready_i = '0' and awvalid = '1' ", 3)
        s += "and wvalid = '1') then\n"
        s += indentString("awaddr_i <= awaddr;\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_awaddr;\n')
        s += '\n'

        s += indentString('p_wready : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("wready_i <= '0';\n", 4)
        s += indentString("elsif (wready_i = '0' and awvalid = '1' ", 3)
        s += "and wvalid = '1') then\n"
        s += indentString("wready_i <= '1';\n", 4)
        s += indentString('else\n', 3)
        s += indentString("wready_i <= '0';\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_wready;\n')
        s += '\n'

        s += indentString('slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;\n')
        s += '\n'
        s += indentString('p_mm_select_write : process(clk)\n')
        s += indentString('begin\n')

        s += indentString('if rising_edge(clk) then\n', 2)
        
        s += indentString("if areset_n = '0' then\n", 3)

        # Assign default values
        s += indentString('\naxi_rw_regs_i <= c_', 4)
        s += self.name + '_rw_regs;\n\n'

        
        s += indentString("elsif (slv_reg_wren = '1') then\n", 3)
        s += '\n'
        s += indentString('case awaddr_i is\n\n', 4)

        # create a generator for looping through all rw regs
        gen = (reg for reg in self.registers if reg.mode == "rw")
        for reg in gen:
            s += indentString('when C_ADDR_', 5)
            s += reg.name.upper() + ' =>\n\n'
            par = ''
            if reg.sig_type == 'record':

                lasthigh = -1
                for entry in reg.fields:
                    par += 'axi_rw_regs_i.' + reg.name + '.' + entry['name']
                    par += ' <= wdata('
                    if entry['type'] == 'sl':
                        lasthigh += 1
                        par += str(lasthigh)
                    elif entry['type'] == 'slv':
                        lasthigh += 1
                        par += str(entry['length'] + lasthigh - 1)
                        par += ' downto '
                        par += str(lasthigh)
                        lasthigh += entry['length'] - 1
                    else:
                        raise UndefinedEntryType(
                            "Unknown entry type: " + entry['type'])
                    par += ');\n'

            elif reg.sig_type == 'default':
                par += 'axi_rw_regs_i.' + reg.name + ' <= wdata;\n'
            elif reg.sig_type == 'slv':
                par += 'axi_rw_regs_i.' + reg.name + ' <= wdata('
                par += str(reg.length - 1) + ' downto 0);\n'
            elif reg.sig_type == 'sl':
                par += 'axi_rw_regs_i.' + reg.name + ' <= wdata(0);\n'
            else:
                raise UndefinedRegisterType(
                    "Unknown register type: " + reg.sig_type)
            s += indentString(par, 6)
            s += '\n'

        s += indentString('when others =>\n', 5)
        s += indentString('null;\n', 6)
        s += '\n'
        s += indentString('end case;\n', 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_mm_select_write;\n')
        s += '\n'

        s += indentString('p_write_response : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("bvalid_i <= '0';\n", 4)
        s += indentString('bresp_i  <= "00";\n', 4)
        s += indentString("elsif (awready_i = '1' and awvalid = '1' and ", 3)
        s += "wready_i = '1' and wvalid = '1' and bvalid_i = '0') then\n"
        s += indentString("bvalid_i <= '1';\n", 4)
        s += indentString('bresp_i  <= "00";\n', 4)
        s += indentString("elsif (bready = '1' and bvalid_i = '1') then\n", 3)
        s += indentString("bvalid_i <= '0';\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_write_response;\n')
        s += '\n'

        s += indentString('p_arready : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("arready_i <= '0';\n", 4)
        s += indentString("araddr_i  <= (others => '0');\n", 4)
        s += indentString("elsif (arready_i = '0' and arvalid = '1') then\n", 3)
        s += indentString("arready_i <= '1';\n", 4)
        s += indentString('araddr_i  <= araddr;\n', 4)
        s += indentString('else\n', 3)
        s += indentString("arready_i <= '0';\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_arready;\n')
        s += '\n'

        s += indentString('p_arvalid : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("rvalid_i <= '0';\n", 4)
        s += indentString('rresp_i  <= "00";\n', 4)
        s += indentString("elsif (arready_i = '1' and arvalid = '1' and ", 3)
        s += "rvalid_i = '0') then\n"
        s += indentString("rvalid_i <= '1';\n", 4)
        s += indentString('rresp_i  <= "00";\n', 4)
        s += indentString("elsif (rvalid_i = '1' and rready = '1') then\n", 3)
        s += indentString("rvalid_i <= '0';\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_arvalid;\n')
        s += '\n'

        s += indentString('slv_reg_rden <= arready_i and arvalid and ')
        s += '(not rvalid_i);\n'
        s += '\n'
        s += indentString('p_mm_select_read : process (all)\n')
        s += indentString('begin\n')
        s += '\n'
        s += indentString("reg_data_out <= (others => '0');\n", 2)
        s += '\n'
        s += indentString('case araddr_i is\n', 2)
        s += '\n'
        # Generator for looping through all "readable registers, rw&ro
        gen = [reg for reg in self.registers
               if reg.mode == "ro" or reg.mode == "rw"]
        for reg in gen:
            s += indentString('when C_ADDR_', 3)
            s += reg.name.upper() + ' =>\n\n'
            par = ''

            if reg.sig_type == 'record':

                lasthigh = -1
                for entry in reg.fields:
                    lasthigh += 1
                    par += 'reg_data_out('

                    if entry['type'] == 'sl':
                        par += str(lasthigh)
                    elif entry['type'] == 'slv':
                        par += str(entry['length'] + lasthigh - 1)
                        par += ' downto ' + str(lasthigh)
                        lasthigh += entry['length'] - 1
                    else:
                        raise UndefinedEntryType(
                            'Unknown entry type: ' + entry['type'])
                    if reg.mode == 'rw':
                        par += ') <= axi_rw_regs_i.'
                    elif reg.mode == 'ro':
                        par += ') <= axi_ro_regs.'
                    else:
                        raise Exception("Unknown error occurred")
                    par += reg.name + '.' + entry['name'] + ';\n'

            elif reg.sig_type == 'default':
                par += 'reg_data_out <= '
                if reg.mode == 'rw':
                    par += 'axi_rw_regs_i.'
                elif reg.mode == 'ro':
                    par += 'axi_ro_regs.'
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ';\n'

            elif reg.sig_type == 'slv':
                par += 'reg_data_out('
                par += str(reg.length - 1) + ' downto 0) <= '
                if reg.mode == 'rw':
                    par += 'axi_rw_regs_i.'
                elif reg.mode == 'ro':
                    par += 'axi_ro_regs.'
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ';\n'

            elif reg.sig_type == 'sl':
                par += 'reg_data_out(0) <= '
                if reg.mode == 'rw':
                    par += 'axi_rw_regs_i.'
                elif reg.mode == 'ro':
                    par += 'axi_ro_regs.'
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ';\n'

            else:
                raise UndefinedRegisterType(
                    "Unknown register type: " + reg.sig_type)
            s += indentString(par, 4)
            s += '\n'

        s += indentString('when others =>\n', 3)
        s += indentString('null;\n', 4)
        s += '\n'
        s += indentString('end case;\n', 2)
        s += indentString('end process p_mm_select_read;\n')
        s += '\n'

        s += indentString('p_output : process(clk)\n')
        s += indentString('begin\n')
        s += indentString('if rising_edge(clk) then\n', 2)
        s += indentString("if areset_n = '0' then\n", 3)
        s += indentString("rdata_i <= (others => '0');\n", 4)
        s += indentString("elsif (slv_reg_rden = '1') then\n", 3)
        s += indentString("rdata_i <= reg_data_out;\n", 4)
        s += indentString('end if;\n', 3)
        s += indentString('end if;\n', 2)
        s += indentString('end process p_output;\n')
        s += '\n'

        s += 'end behavior;'

        return s

    def returnModulePkgVHDL(self):
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += "package " + self.name + "_pkg is"
        s += "\n\n"

        par = ''
        par += "constant C_" + self.name.upper()
        par += "_ADDR_WIDTH : natural := " + str(self.addrWidth) + ";\n"
        par += "constant C_" + self.name.upper()
        par += "_DATA_WIDTH : natural := " + str(self.dataWidth) + ";\n"
        par += "\n"

        par += "subtype t_" + self.name + "_addr is "
        par += "std_logic_vector(C_" + self.name.upper() + "_ADDR_WIDTH-1 "
        par += "downto 0);\n"

        par += "subtype t_" + self.name + "_data is "
        par += "std_logic_vector(C_" + self.name.upper() + "_DATA_WIDTH-1 "
        par += "downto 0);\n"
        par += "\n"

        for reg in self.registers:
            par += "constant C_ADDR_" + reg.name.upper()
            par += " : t_" + self.name + "_addr := " + str(self.addrWidth)
            par += 'X"' + '%X' % reg.address + '";\n'
        par += '\n'
        s += indentString(par)

        s += indentString("-- RW Register Record Definitions\n\n")

        # Create all types for RW registers with records
        for reg in self.registers:
            if reg.mode == "rw" and reg.sig_type == "record":
                s += indentString("type t_" + self.name + "_rw_")
                s += reg.name + " is record\n"

                for j in reg.fields:
                    s += indentString(j['name'], 2) + " : "
                    if j['type'] == "slv":
                        s += "std_logic_vector(" + str(j['length'] - 1)
                        s += " downto 0);\n"
                    elif j['type'] == "sl":
                        s += "std_logic;\n"
                    else:
                        raise RuntimeError(
                            "Something went wrong..." + j['type'])
                s += indentString("end record;\n\n")

        # The RW register record type
        s += indentString("type t_" + self.name + "_rw_regs is record\n")
        for reg in self.registers:
            if reg.mode == "rw":
                s += indentString(reg.name, 2) + " : "
                if reg.sig_type == "default" or (reg.sig_type == "slv" and reg.length == self.dataWidth):
                    s += "t_" + self.name + "_data;\n"
                elif reg.sig_type == "slv":
                    s += "std_logic_vector(" + \
                        str(reg.length - 1) + " downto 0);\n"
                elif reg.sig_type == "sl":
                    s += "std_logic;\n"
                elif reg.sig_type == "record":
                    s += "t_" + self.name + "_rw_" + reg.name + ";\n"
                else:
                    raise RuntimeError("Something went wrong...")
        s += indentString("end record;\n")
        s += "\n"

        s += indentString("-- RW Register Reset Value Constant\n\n")

        s += indentString("constant c_") + self.name + "_rw_regs : t_"
        s += self.name + "_rw_regs := (\n"
        gen = [reg for reg in self.registers if reg.mode == 'rw']

        for i, reg in enumerate(gen):
            par = ''
            par += reg.name + ' => '

            # RW default values must be declared
            if reg.sig_type == 'default' or reg.sig_type == 'slv':
                if reg.reset == "0x0":
                    par += "(others => '0')"
                else:
                    par += str(reg.length) + 'X"'
                    par += format(int(reg.reset, 16), 'X') + '"'

            elif reg.sig_type == 'record':

                if len(reg.fields) > 1:
                    par += '(\n'
                else:
                    par += '('

                for j, entry in enumerate(reg.fields):
                    if len(reg.fields) > 1:
                        par += indentString(entry['name'] + ' => ')
                    else:
                        par += entry['name'] + ' => '

                    if entry['type'] == 'slv':

                        if entry['reset'] == "0x0":
                            par += "(others => '0')"
                        else:
                            par += str(entry['length']) + 'X"'
                            par += format(int(entry['reset'], 16), 'X') + '"'

                    elif entry['type'] == 'sl':
                        par += "'" + format(int(entry['reset'], 16), 'X') + "'"

                    else:
                        raise UndefinedEntryType(
                            "Unknown entry type: " + entry['type'])

                    if j < len(reg.fields) - 1:
                        par += ',\n'

                par += ')'

            elif reg.sig_type == 'sl':
                par += "'" + format(int(reg.reset, 16), 'X') + "'"

            if i < len(gen) - 1:
                par += ','
            else:
                par += ');'
            par += '\n'

            s += indentString(par, 2)
        s += '\n'

        s += indentString("-- RO Register Record Definitions\n\n")

        # Create all types for RO registers with records
        for reg in self.registers:
            if reg.mode == "ro" and reg.sig_type == "record":
                s += indentString("type t_" + self.name + "_ro_")
                s += reg.name + " is record\n"

                for j in reg.fields:
                    s += indentString(j['name'], 2) + " : "
                    if j['type'] == "slv":
                        s += "std_logic_vector(" + str(j['length'] - 1)
                        s += " downto 0);\n"
                    elif j['type'] == "sl":
                        s += "std_logic;\n"
                    else:
                        raise RuntimeError("Something went wrong... WTF?")
                s += indentString("end record;\n\n")

        # The RO register record type
        s += indentString("type t_" + self.name + "_ro_regs is record\n")
        for reg in self.registers:
            if reg.mode == "ro":
                s += indentString(reg.name, 2) + " : "
                if reg.sig_type == "default" or (reg.sig_type == "slv" and reg.length == self.dataWidth):
                    s += "t_" + self.name + "_data;\n"
                elif reg.sig_type == "slv":
                    s += "std_logic_vector(" + \
                        str(reg.length - 1) + " downto 0);\n"
                elif reg.sig_type == "sl":
                    s += "std_logic;\n"
                elif reg.sig_type == "record":
                    s += "t_" + self.name + "_ro_" + reg.name + ";\n"
                else:
                    raise RuntimeError(
                        "Something went wrong... What now?" + reg.sig_type)
        s += indentString("end record;\n")
        s += "\n"

        s += indentString("-- RO Register Reset Value Constant\n\n")

        s += indentString("constant c_") + self.name + "_ro_regs : t_"
        s += self.name + "_ro_regs := (\n"
        gen = [reg for reg in self.registers if reg.mode == 'ro']

        for i, reg in enumerate(gen):
            par = ''
            par += reg.name + ' => '

            # RO default values must be declared
            if reg.sig_type == 'default' or reg.sig_type == 'slv':
                if reg.reset == "0x0":
                    par += "(others => '0')"
                else:
                    par += str(reg.length) + 'X"'
                    par += format(int(reg.reset, 16), 'X') + '"'

            elif reg.sig_type == 'record':

                if len(reg.fields) > 1:
                    par += '(\n'
                else:
                    par += '('

                for j, entry in enumerate(reg.fields):
                    if len(reg.fields) > 1:
                        par += indentString(entry['name'] + ' => ')
                    else:
                        par += entry['name'] + ' => '

                    if entry['type'] == 'slv':

                        if entry['reset'] == "0x0":
                            par += "(others => '0')"
                        else:
                            par += str(entry['length']) + 'X"'
                            par += format(int(entry['reset'], 16), 'X') + '"'

                    elif entry['type'] == 'sl':
                        par += "'" + format(int(entry['reset'], 16), 'X') + "'"

                    else:
                        raise UndefinedEntryType(
                            "Unknown entry type: " + entry['type'])

                    if j < len(reg.fields) - 1:
                        par += ',\n'

                par += ')'

            elif reg.sig_type == 'sl':
                par += "'" + format(int(reg.reset, 16), 'X') + "'"

            if i < len(gen) - 1:
                par += ','
            else:
                par += ');'
            par += '\n'

            s += indentString(par, 2)
        s += '\n'

        s += "end package " + self.name + "_pkg;"

        return s

    def returnModuleVHDL(self):
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += 'use work.' + self.busType + '_pkg.all;\n'
        s += 'use work.' + self.name + '_pkg.all;\n'
        s += '\n'

        s += 'entity ' + self.name + ' is\n'
        s += '\n'
        s += indentString('port (\n')
        s += '\n'
        par = ''
        par += '-- ' + self.busType.upper() + ' Bus Interface\n'
        par += self.busType + '_clk      : in  std_logic;\n'
        par += self.busType + '_areset_n : in  std_logic;\n'
        par += self.busType + '_in       : in  t_' + \
            self.busType + '_interconnect_to_slave;\n'
        par += self.busType + '_out      : out t_' + \
            self.busType + '_slave_to_interconnect\n'
        par += ');\n'
        s += indentString(par, 2)
        s += '\n'
        s += 'end entity ' + self.name + ';\n'
        s += '\n'

        s += 'architecture behavior of ' + self.name + ' is\n'
        s += '\n'

        s += indentString('signal ' + self.busType + '_rw_regs : t_')
        s += self.name + '_rw_regs := c_' + self.name + '_rw_regs;\n'
        s += indentString('signal ' + self.busType + '_ro_regs : t_')
        s += self.name + '_ro_regs := c_' + self.name + '_ro_regs;\n'

        s += '\n'

        s += 'begin\n'
        s += '\n'

        s += indentString('i_' + self.name + '_' + self.busType + '_pif ')
        s += ': entity work.' + self.name + '_' + self.busType + '_pif\n'
        s += indentString('port map (\n', 2)

        par = ''
        par += self.busType + '_ro_regs => ' + self.busType + '_ro_regs,\n'
        par += self.busType + '_rw_regs => ' + self.busType + '_rw_regs,\n'
        par += 'clk         => ' + self.busType + '_clk,\n'
        par += 'areset_n    => ' + self.busType + '_areset_n,\n'
        par += 'awaddr      => ' + self.busType + '_in.awaddr(C_'
        par += self.name.upper() + '_ADDR_WIDTH-1 downto 0),\n'
        par += 'awvalid     => ' + self.busType + '_in.awvalid,\n'
        par += 'awready     => ' + self.busType + '_out.awready,\n'
        par += 'wdata       => ' + self.busType + '_in.wdata(C_'
        par += self.name.upper() + '_DATA_WIDTH-1 downto 0),\n'
        par += 'wvalid      => ' + self.busType + '_in.wvalid,\n'
        par += 'wready      => ' + self.busType + '_out.wready,\n'
        par += 'bresp       => ' + self.busType + '_out.bresp,\n'
        par += 'bvalid      => ' + self.busType + '_out.bvalid,\n'
        par += 'bready      => ' + self.busType + '_in.bready,\n'
        par += 'araddr      => ' + self.busType + '_in.araddr(C_'
        par += self.name.upper() + '_ADDR_WIDTH-1 downto 0),\n'
        par += 'arvalid     => ' + self.busType + '_in.arvalid,\n'
        par += 'arready     => ' + self.busType + '_out.arready,\n'
        par += 'rdata       => ' + self.busType + '_out.rdata(C_'
        par += self.name.upper() + '_DATA_WIDTH-1 downto 0),\n'
        par += 'rresp       => ' + self.busType + '_out.rresp,\n'
        par += 'rvalid      => ' + self.busType + '_out.rvalid,\n'
        par += 'rready      => ' + self.busType + '_in.rready\n'
        par += ');\n'
        s += indentString(par, 3)

        # If bus data width is larger than module data width, set the unused bits to zero
        if self.busDataWitdh > self.dataWidth:
            s += indentString('-- Set unused bus data bits to zero\n')
            s += indentString(self.busType +
                              '_out.rdata(C_' + self.busType.upper())
            s += '_DATA_WIDTH-1 downto C_' + self.name.upper() + '_DATA_WIDTH)'
            s += " <= (others => '0');\n"

        s += '\n'
        s += 'end architecture behavior;'

        return s

    def printJSON(self, includeAddress=False):
        """! @brief Returns JSON string

        """
        dic = OrderedDict()

        dic["name"] = self.name
        dic["addr_width"] = self.addrWidth
        dic["data_width"] = self.dataWidth

        dic["register"] = []

        for i, reg in enumerate(self.registers):
            regDic = OrderedDict()

            regDic["name"] = reg.name
            regDic["mode"] = reg.mode
            regDic["type"] = reg.sig_type

            if includeAddress:
                regDic["address"] = str(hex(reg.address))

            if (reg.sig_type != "default" and reg.sig_type != "record" and
                    reg.sig_type != "sl"):
                regDic["length"] = reg.length

            if reg.sig_type != "record":
                regDic["reset"] = reg.reset

            if reg.sig_type == "record" and len(reg.fields) > 0:

                regDic["entries"] = reg.fields

            regDic["description"] = reg.description

            dic["register"].append(regDic)

        dic["description"] = self.description

        return json.dumps(dic, indent=4)

    def getNextAddress(self):
        """! @brief Will get the next address based on the byte-addressed scheme

        """
        addr = 0
        foundAddr = False
        while (not foundAddr):
            self.isAddressOutOfRange(addr)
            if self.isAddressFree(addr):
                self.addresses.append(addr)
                return addr
            else:
                # force integer division to prevent float
                addr += self.dataWidth // 8

    def isAddressOutOfRange(self, addr):
        if addr > pow(2, self.addrWidth) - 1:
            raise RuntimeError("Address " + hex(addr) +
                               " is definetely out of range...")
        return True

    def isAddressFree(self, addr):
        for address in self.addresses:
            if address == addr:
                return False
        # If loop completes without matching addresses
        return True

    def registerValid(self, reg):
        if set(("name", "mode", "type", "description")).issubset(reg):
            return True
        else:
            return False

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addrWidth) + "\n"
        string += "Data width: " + str(self.dataWidth) + "\n"
        string += "Description: " + self.description + "\n\n"
        string += "Registers: \n"
        for i, reg in enumerate(self.registers):
            string += indentString(str(reg), 1)
        return string


