from utils import indentString
from utils import jsonParser
from exceptions import *


def test():
    try:
        
        a = jsonParser()
        mod = Module(a)
        print(mod)
        print(mod.returnModulePkgVHDL())

        print(mod.printJSON(True))
        print(mod.returnRegisterPIFVHDL())

    except Exception as e:
        print(str(e))

class Module:
    """! @brief


    """

    def __init__(self, mod):
        """! @brief

        """
        self.name = mod['name']
        self.addr_width = mod['addr_width']
        self.data_width = mod['data_width']
        self.description = mod['description']
        self.registers = []
        self.addresses = []
        self.addRegisters(mod['register'])
        
        

    def addRegisters(self, regs):
        for i in regs:
            if self.registerValid(i):
                # Check if size is specified
                if "address" in i:
                    addr = int(i['address'], self.addr_width)
                    if self.isAddressIsFree(addr):
                        self.isAddressOutOfRange(addr)
                        self.addresses.append(addr)
                        self.registers.append(Register(i, addr,
                                                       self.data_width))
                    else:
                        raise InvalidAddress(i['name'], addr)
                else:
                    self.registers.append(Register(i, self.getNextAddress(),
                                                   self.data_width))
            else:
                raise InvalidRegister(i)

    def returnRegisterPIFVHDL(self):
        s = 'use work.' + self.name + '.all;\n\n'
        s += 'entity ' + self.name + '_axi_pif is\n\n'

        s += indentString('port (') + '\n'

        s += indentString('-- register record signals', 2) + '\n'
        s += indentString('axi_ro_regs : in  t_', 2) + self.name + '_ro_regs;\n'
        s += indentString('axi_rw_regs : out t_', 2) + self.name + '_rw_regs;\n'
        s += '\n'
        s += indentString('-- bus signals', 2) + '\n'
        s += indentString('clk         : in  std_logic', 2) + ':\n'
        s += indentString('areset_n    : in  std_logic', 2) + ';\n'
        s += indentString('awaddr      : in  t_', 2) + self.name + '_addr' + ';\n'
        s += indentString('awvalid     : in  std_logic', 2) + ';\n'
        s += indentString('awready     : out std_logic', 2) + ';\n'
        s += indentString('wdata       : in  t_', 2) + self.name + '_data' + ';\n'
        s += indentString('wvalid      : in  std_logic', 2) + ';\n'
        s += indentString('wready      : out std_logic', 2) + ';\n'
        s += indentString('bresp       : out std_logic_vector(1 downto 0)', 2) + ';\n'
        s += indentString('bvalid      : out std_logic', 2) + ';\n'
        s += indentString('bready      : in  std_logic', 2) + ';\n'
        s += indentString('araddr      : in  t_', 2) + self.name + '_addr' + ';\n'
        s += indentString('arvalid     : in  std_logic', 2) + ';\n'
        s += indentString('arready     : out std_logic', 2) + ';\n'
        s += indentString('rdata       : out t_', 2) + self.name + '_data' + ';\n'
        s += indentString('rresp       : out std_logic_vector(1 downto 0)', 2) + ';\n'
        s += indentString('rvalid      : out std_logic', 2) + ';\n'
        s += indentString('rready      : in  std_logic', 2) + '\n'
        s += indentString(');', 2) + '\n'
        s += 'end ' + self.name + '_axi_pif;\n\n'

        s += 'architecture behavior of ' + self.name + '_axi_pif is\n\n'

        s += indentString('-- internal signal for readback') + '\n'
        s += indentString('signal axi_rw_regs_i : t_')
        s += self.name + '_rw_regs;\n\n'

        s += indentString('-- internal bus signals for readback') + '\n'
        s += indentString('signal awaddr_i      : t_') + self.name + '_addr;\n'
        s += indentString('signal awready_i     : std_logic') + ';\n'
        s += indentString('signal wready_i      : std_logic') + ';\n'
        s += indentString('signal bresp_i       : std_logic_vector(1 downto 0)')
        s += ';\n'
        s += indentString('signal bvalid_i      : std_logic') + ';\n'
        s += indentString('signal araddr_i      : t_') + self.name + '_addr;\n'
        s += indentString('signal arready_i     : std_logic') + ';\n'
        s += indentString('signal rdata_i       : t_') + self.name + '_data;\n'
        s += indentString('signal rresp_i       : std_logic_vector(1 downto 0)')
        s += ';\n'
        s += indentString('signal rvalid_i      : std_logic') + ';\n\n'

        s += indentString('signal slv_reg_rden : std_logic') + ';\n'
        s += indentString('signal slv_reg_wren : std_logic') + ';\n'
        s += indentString('signal reg_data_out : t_') + self.name + '_data;\n'
        s += indentString('signal byte_index   : integer') + '; -- unused\n'
        s += '\n'

        s += 'begin\n\n'
        s += indentString('axi_rw_regs <= axi_rw_regs_i') + ';\n'
        s += '\n'

        s += indentString('awready <= awready_i') + ';\n'
        s += indentString('wready  <= wready_i') + ';\n'
        s += indentString('bresp   <= bresp_i') + ';\n'
        s += indentString('bvalid  <= bvalid_i') + ';\n'
        s += indentString('arready <= arready_i') + ';\n'
        s += indentString('rdata   <= rdata_i') + ';\n'
        s += indentString('rresp   <= rresp_i') + ';\n'
        s += indentString('rvalid  <= rvalid_i') + ';\n'
        s += '\n'

        
        return s


    def returnModulePkgVHDL(self):
        s = "package " + self.name + "_pkg is"
        s += "\n\n"
        s += indentString("constant C_" + self.name.upper())
        s += "_ADDR_WIDTH : natural := " + str(self.addr_width) + ";\n"
        s += indentString("constant C_" + self.name.upper())
        s += "_DATA_WIDTH : natural := " + str(self.data_width) + ";\n"
        s += "\n"

        s += indentString("subtype t_" + self.name + "_addr is ")
        s += "std_logic_vector(C_" + self.name.upper() + "_ADDR_WIDTH-1 "
        s += "downto 0);\n"

        s += indentString("subtype t_" + self.name + "_data is ")
        s += "std_logic_vector(C_" + self.name.upper() + "_DATA_WIDTH-1 "
        s += "downto 0);\n"
        s += "\n"

        for i in self.registers:
            s += indentString("constant C_ADDR_" + i.name.upper())
            s += " : t_" + self.name + "_addr := " + str(self.addr_width)
            s += 'X"' + '%X' % i.address + '";\n'

        s += '\n'
        # Create all types for RW registers with records
        for i in self.registers:
            if i.mode == "rw" and i.regtype == "record":
                s += indentString("type t_" + self.name + "_rw_")
                s += i.name + " is record\n"

                for j in i.entries:
                    s += indentString(j['name'], 2) + " : "
                    if j['type'] == "slv":
                        s += "std_logic_vector(" + str(j['length']-1)
                        s += " downto 0);\n"
                    elif j['type'] == "sl":
                        s += "std_logic;\n"
                    else:
                        raise RuntimeError("Something went wrong..." + j['type'])
                s += indentString("end record;\n")
        s += "\n"

                
        # The RW register record type
        s += indentString("type t_" + self.name + "_rw_regs is record")
        s += "\n"
        for i in self.registers:
            if i.mode == "rw":
                s += indentString(i.name, 2) + " : "
                if i.regtype == "default" or (i.regtype == "slv" and i.length == self.data_width):
                    s += "t_" + self.name + "_data;\n"
                elif i.regtype == "slv":
                    s += "std_logic_vector(" + str(i.length-1) + " downto 0);\n"
                elif i.regtype == "sl":
                    s += "std_logic;\n"
                elif i.regtype == "record":
                    s += "t_" + self.name + "_rw_" + i.name + ";\n"
                else:
                    raise RuntimeError("Something went wrong... What?")
        s += indentString("end record;\n")
        s += "\n"

        # Create all types for RO registers with records
        for i in self.registers:
            if i.mode == "ro" and i.regtype == "record":
                s += indentString("type t_" + self.name + "_ro_")
                s += i.name + " is record\n"

                for j in i.entries:
                    s += indentString(j['name'], 2) + " : "
                    if j['type'] == "slv":
                        s += "std_logic_vector(" + str(j['length']-1)
                        s += " downto 0);\n"
                    elif j['type'] == "sl":
                        s += "std_logic;\n"
                    else:
                        raise RuntimeError("Something went wrong... WTF?")
                s += indentString("end record;\n")
        s += "\n"

        # The RO register record type
        s += indentString("type t_" + self.name + "_ro_regs is record")
        s += "\n"
        for i in self.registers:
            if i.mode == "ro":
                s += indentString(i.name, 2) + " : "
                if i.regtype == "default" or (i.regtype == "slv" and i.length == self.data_width):
                    s += "t_" + self.name + "_data;\n"
                elif i.regtype == "slv":
                    s += "std_logic_vector(" + str(i.length-1) + " downto 0);\n"
                elif i.regtype == "sl":
                    s += "std_logic;\n"
                elif i.regtype == "record":
                    s += "t_" + self.name + "_ro_" + i.name + ";\n"
                else:
                    raise RuntimeError("Something went wrong... What now?" + i.regtype)
        s += indentString("end record;\n")
        s += "\n"

        s += "end package " + self.name + "_pkg;"
        
        return s
        

    def printJSON(self, includeAddress=False):
        """! @brief Returns JSON string

        """
        string = '{ "name": "'
        string += self.name + '",\n'
        string += indentString('"addr_width": ')
        string += str(self.addr_width) + ',\n'
        string += indentString('"data_width": ')
        string += str(self.data_width) + ',\n'

        string += indentString('"register": [') + '\n'

        for i, reg in enumerate(self.registers):

            string += indentString('{"name": "', 3)
            string += reg.name + '",\n'
            string += indentString('"mode": "', 3)
            string += reg.mode + '",\n'
            string += indentString('"type": "', 3)
            string += reg.regtype + '",\n'

            if includeAddress:
                string += indentString('"address": "', 3)
                string += str(hex(reg.address)) + '",\n'

            if reg.length != 0:

                string += indentString('"length": ', 3)
                string += str(reg.length) + ',\n'

            if len(reg.entries) > 0:
                string += indentString('"entries": [', 3) + '\n'

                for j, entry in enumerate(reg.entries):
                    string += indentString('{"name": "', 4)
                    string += entry['name'] + '", "type": "' + entry['type'] + '"'

                    if entry['type'] == 'slv':
                        string += ', "length": ' + str(entry['length'])

                    if j < len(reg.entries)-1:
                        string += '},\n'
                    else:
                        string += '}\n'
                        

                string += indentString('],', 3) + '\n'
                
            string += indentString('"description": "', 3)
            string += reg.description + '"\n'

            if i < len(self.registers)-1:
                string += indentString('},', 3) + '\n'
            else:
                string += indentString('}', 3) + '\n'

        string += indentString('],', 2) + '\n'
        string += indentString('"description": "', 2)
        string += self.description + '"\n'

        string += '}'

        return string
        

    def getNextAddress(self):
        """! @brief Will get the next address based on the byte-addressed scheme
        
        """
        addr = 0
        foundAddr = False
        while (not foundAddr):
            self.isAddressOutOfRange(addr)
            if self.isAddressIsFree(addr):
                self.addresses.append(addr)
                return addr
            else:
                # force integer division to prevent float
                addr += self.data_width//8

    def isAddressOutOfRange(self, addr):
        if addr > pow(2, self.addr_width)-1:
            raise RuntimeError("Address " + hex(addr) + " is definetely out of range...")
        return True

    def isAddressIsFree(self, addr):
        for i in self.addresses:
            if i == addr:
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
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + self.description + "\n"
        for i, reg in enumerate(self.registers):
            string += "Register " + str(i) + "\n"
            string += indentString(str(reg), 2) +"\n"
        return string



class Register:
    """! @brief


    """

    def __init__(self, reg, address, mod_data_length):
        self.name = reg['name']
        self.mode = reg['mode']
        self.description = reg['description']
        self.address = address
        self.regtype = ""
        self.length = 0
        self.entries = []
        
        if reg['type'] == 'default':
           self.regtype = 'default'
        elif reg['type'] == 'slv':
            self.regtype = 'slv'
            self.length = reg['length']
        elif reg['type'] == 'sl':
            self.regtype = 'sl'
            self.length = 0
        elif reg['type'] == 'record':
            self.regtype = 'record'
            for entry in reg['entries']:
                if entry['type'] == 'slv':
                    self.entries.append({'name': entry['name'],
                                        'type': 'slv',
                                         'length': entry['length']})
                    self.length += entry['length']
                elif entry['type'] == 'sl':
                    self.entries.append({'name': entry['name'],
                                         'type': 'sl', 'length': 1})
                    self.length += 1
                else:
                    raise UndefinedEntryType(entry['type'])
        else:
            raise UndefinedRegisterType(reg['type'])

        # Perform check that data bits are not exceeded
        self.checkRegisterDataLength(mod_data_length)
        

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string = "Address: " + hex(self.address) + "\n"
        string += "Mode: " + self.mode + "\n"
        string += "Type: " + self.regtype + "\n"
        string += "Length: " + str(self.length)
        if self.regtype == 'record':

            for i in self.entries:
                string += "\n"
                string += indentString("Name: " + i['name'] +
                                       " Type: " + i['type'] +
                                       " Length: " + str(i['length']))

        string += "\nDescription: " + self.description
        return string

    def checkRegisterDataLength(self, module):
        """! @brief Controls that the combined data bits in entries does not 
        exceed data bits of module
        
        """
        if self.length > module:
            raise ModuleDataBitsExceeded(self.name, self.length, module)
