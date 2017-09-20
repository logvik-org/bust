from utils import *
from exceptions import *


def test():
    try:
        
        a = jsonParser()
        reg0 = a['register'][0]
        print(Register(reg0, 16))

        reg1 = a['register'][1]
        print(Register(reg1, 16))

        reg2 = a['register'][2]
        print(Register(reg2, 16))

        reg3 = a['register'][3]
        print(Register(reg3, 16))

        reg4 = a['register'][4]
        print(Register(reg4, 16))

    except Exception as e:
        print(str(e))

class Module:
    """! @brief


    """

    def __init__(self, name, addr_width, data_width, description):
        """! @brief

        """
        self.__name = name
        self.__addr_width = addr_width
        self.__data_width = data_width
        self.__description = description
        self.__registers = []
        

    def addRegisters(self, regs):
        for i in len(regs):
            self.__registers.append(Register(regs[i]))

    def printJSON(self, filename):
        """! @brief

        """

class Register:
    """! @brief


    """

    def __init__(self, reg, mod_data_length):
        self.name = reg['name']
        self.mode = reg['mode']
        self.description = reg['description']
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
        string += "Mode: " + self.mode + "\n"
        string += "Type: " + self.regtype + "\n"
        string += "Length: " + str(self.length)
        if self.regtype == 'record':

            for i in self.entries:
                string += "\n"
                string += indentString("Name: " + i['name'] +
                                       " Type: " + i['type'] +
                                       " Length: " + str(i['length']))

        string += "\nDescription: " + self.description + "\n"
        return string

    def checkRegisterDataLength(self, module):
        """! @brief Controls that the combined data bits in entries does not 
        exceed data bits of module
        
        """
        if self.length > module:
            raise ModuleDataBitsExceeded(self.name, self.length, module)
