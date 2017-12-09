from utils import indentString
from utils import add_line_breaks

from exceptions import UndefinedRegisterType
from exceptions import UndefinedEntryType
from exceptions import InvalidRegisterFormat
from exceptions import ModuleDataBitsExceeded

from collections import OrderedDict


class Register:
    """! @brief Managing register information


    """

    def __init__(self, reg, address, mod_data_length):
        self.name = reg['name']
        self.mode = reg['mode']
        self.description = add_line_breaks(reg['description'], 25)
        self.address = address
        self.sig_type = ""
        self.reset = "0x0"
        self.length = 0
        self.fields = []

        # Assign the reg type and register data length
        if reg['type'] == 'default':
            self.sig_type = 'default'
            self.length = mod_data_length

        elif reg['type'] == 'slv':
            self.sig_type = 'slv'
            self.length = reg['length']

        elif reg['type'] == 'sl':
            self.sig_type = 'sl'

            if 'length' in reg and reg['length'] != 1:
                raise UndefinedRegisterType("SL cannot have length other than 1")
            else:
                self.length = 1

        elif reg['type'] == 'record':
            self.sig_type = 'record'

            for entry in reg['entries']:
                entryDic = OrderedDict([('name', entry['name']),
                                        ('type', ''),
                                        ('length', 0),
                                        ('pos_high', 0),
                                        ('pos_low', self.getNextPosLow()),
                                        ('reset', '0x0'),
                                        ('description', '')])

                if entry['type'] == 'slv':
                    entryDic['type'] = 'slv'
                    entryDic['length'] = entry['length']

                elif entry['type'] == 'sl':
                    entryDic['type'] = 'sl'
                    entryDic['length'] = 1
                else:
                    raise UndefinedEntryType(entry['type'])

                self.length += entryDic['length']

                posHigh = entryDic['pos_high'] = entryDic['pos_low'] + entryDic['length'] - 1
                if posHigh > self.length:
                    raise InvalidRegisterFormat('Entry lengths are longer than register length: ' +
                                                entryDic['name'] + ' in reg: ' + self.name)
                else:
                    entryDic['pos_high'] = posHigh

                if 'reset' in entry:
                    # Check whether reset value matches entry length
                    # maxvalue is given by 2^length
                    maxvalue = (2 ** entryDic['length']) - 1
                    if maxvalue < int(entry['reset'], 16):
                        raise InvalidRegisterFormat("Reset value does not match entry: " +
                                                    entryDic['name'] +
                                                    " in reg: " + self.name)
                    else:
                        entryDic['reset'] = entry['reset']
                        regReset = int(self.reset, 16)
                        entryReset = int(entryDic['reset'], 16)
                        regReset += entryReset << entryDic['pos_low']
                        self.reset = hex(regReset)

                if 'description' in entry:
                    entryDic['description'] = entry['description']

                self.fields.append(entryDic)


        else:
            raise UndefinedRegisterType(reg['type'])

        if 'reset' in reg:
            # Reset value is not allowed if sig_type is record
            if reg['type'] == 'record':
                raise InvalidRegisterFormat(
                    "Reset value is not allowed for record type register: " + self.name)
            else:
                # Check whether reset value matches register length
                # maxvalue is given by 2^length
                maxvalue = (2 ** self.length) - 1
                if maxvalue < int(reg['reset'], 16):
                    raise InvalidRegisterFormat("Reset value does not match register: " +
                                                self.name)
                else:
                    self.reset = reg['reset']

        # Perform check that data bits are not exceeded
        self.checkRegisterDataLength(mod_data_length)

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string += "Address: " + hex(self.address) + "\n"
        string += "Mode: " + self.mode + "\n"
        string += "Type: " + self.sig_type + "\n"
        string += "Length: " + str(self.length) + "\n"
        string += "Reset: " + self.reset
        if self.sig_type == 'record':

            for i in self.fields:
                string += "\n"
                string += indentString("Name: " + i['name'] + " Type: " +
                                       i['type'] + " Length: " +
                                       str(i['length']) +
                                       " Reset: " + i['reset'])

        string += "\nDescription: " + self.description + "\n\n"
        return string

    def checkRegisterDataLength(self, module):
        """! @brief Controls that the combined data bits in fields does not
        exceed data bits of module

        """
        if self.length > module:
            raise ModuleDataBitsExceeded(self.name, self.length, module)

    def getNextPosLow(self):
        if len(self.fields) > 0:
            lastPosHigh = self.fields[-1]['pos_high']
            return lastPosHigh + 1
        else:
            return 0
