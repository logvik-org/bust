import utils
from exceptions import *


def test():
    try:
        
        a = utils.jsonParser()
        mod = Module(a)
        print(mod)
        print(mod.writeModulePkgVHDL())
        

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
                    addr = i['address']
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

    def writeModulePkgVHDL(self):
        pkg = "package " + self.name + "_pkg is"
        pkg += "\n\n"
        pkg += utils.indentString("constant C_" + self.name.upper())
        pkg += "_ADDR_WIDTH : natural := " + str(self.addr_width) + ";\n"
        pkg += utils.indentString("constant C_" + self.name.upper())
        pkg += "_DATA_WIDTH : natural := " + str(self.data_width) + ";\n"
        pkg += "\n"

        pkg += utils.indentString("subtype t_" + self.name + "_addr is ")
        pkg += "std_logic_vector(C_" + self.name.upper() + "_ADDR_WIDTH-1 "
        pkg += "downto 0);\n"

        pkg += utils.indentString("subtype t_" + self.name + "_data is ")
        pkg += "std_logic_vector(C_" + self.name.upper() + "_DATA_WIDTH-1 "
        pkg += "downto 0);\n"
        pkg += "\n"

        for i in self.registers:
            pkg += utils.indentString("constant C_ADDR_" + i.name.upper())
            pkg += " : t_" + self.name + "_addr := " + str(self.addr_width)
            pkg += "X\"" + '%X' % i.address + "\";\n"
        pkg += "\n"

        # Create all types for RW registers with records
        for i in self.registers:
            if i.mode == "rw" and i.regtype == "record":
                pkg += utils.indentString("type t_" + self.name + "_rw_")
                pkg += i.name + " is record\n"

                for j in i.entries:
                    pkg += utils.indentString(j['name'], 2) + " : "
                    if j['type'] == "slv":
                        pkg += "std_logic_vector(" + str(j['length']-1)
                        pkg += " downto 0);\n"
                    elif j['type'] == "sl":
                        pkg += "std_logic;\n"
                    else:
                        raise RuntimeError("Something went wrong...")
                pkg += utils.indentString("end record;\n")
        pkg += "\n"

                
        # The RW register record type
        pkg += utils.indentString("type t_" + self.name + "_rw_regs is record")
        pkg += "\n"
        for i in self.registers:
            if i.mode == "rw":
                pkg += utils.indentString(i.name, 2) + " : "
                if i.regtype == "slv" and i.length == self.data_width:
                    pkg += "t_" + self.name + "_data;\n"
                elif i.regtype == "slv":
                    pkg += "std_logic_vector(" + str(i.length-1) + " downto 0);\n"
                elif i.regtype == "sl":
                    pkg += "std_logic;\n"
                elif i.regtype == "record":
                    pkg += "t_" + self.name + "_rw_" + i.name + ";\n"
                else:
                    raise RuntimeError("Something went wrong...")
        pkg += utils.indentString("end record;\n")
        pkg += "\n"

        # Create all types for RO registers with records
        for i in self.registers:
            if i.mode == "ro" and i.regtype == "record":
                pkg += utils.indentString("type t_" + self.name + "_ro_")
                pkg += i.name + " is record\n"

                for j in i.entries:
                    pkg += utils.indentString(j['name'], 2) + " : "
                    if j['type'] == "slv":
                        pkg += "std_logic_vector(" + str(j['length']-1)
                        pkg += " downto 0);\n"
                    elif j['type'] == "sl":
                        pkg += "std_logic;\n"
                    else:
                        raise RuntimeError("Something went wrong...")
                pkg += utils.indentString("end record;\n")
        pkg += "\n"

        # The RO register record type
        pkg += utils.indentString("type t_" + self.name + "_ro_regs is record")
        pkg += "\n"
        for i in self.registers:
            if i.mode == "ro":
                pkg += utils.indentString(i.name, 2) + " : "
                if i.regtype == "slv" and i.length == self.data_width:
                    pkg += "t_" + self.name + "_data;\n"
                elif i.regtype == "slv":
                    pkg += "std_logic_vector(" + str(i.length-1) + " downto 0);\n"
                elif i.regtype == "sl":
                    pkg += "std_logic;\n"
                elif i.regtype == "record":
                    pkg += "t_" + self.name + "_ro_" + i.name + ";\n"
                else:
                    raise RuntimeError("Something went wrong...")
        pkg += utils.indentString("end record;\n")
        pkg += "\n"

        pkg += "end package " + self.name + "_pkg;"
        
        return pkg
        

    def printJSON(self, filename):
        """! @brief

        """

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
            string += utils.indentString(str(reg), 2) +"\n"
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
           self.regtype = 'slv'
           self.length = mod_data_length
        elif reg['type'] == 'slv':
            self.regtype = 'slv'
            self.length = reg['length']
        elif reg['type'] == 'sl':
            self.regtype = 'sl'
            self.length = 1
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
                string += utils.indentString("Name: " + i['name'] +
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
