from utils import indentString

from collections import OrderedDict


class Bus(object):
    """! @brief Managing bus information

    """

    def __init__(self, bus):
        bus = bus['bus']
        if bus['type'] in ['axi']:
            self.bus_type = bus['type']
        else:
            raise InvalidBusType(bus['type'])

        self.data_width = bus['data_width']
        self.addr_width = bus['addr_width']

        if 'reset' not in bus:
            self.bus_reset = 'async'
        elif bus['reset'] in ['async', 'sync']:
            self.bus_reset = bus['reset']
            
        else:
            raise InvalidResetMode(bus['reset'])

    def return_JSON(self):
        json = OrderedDict()
        json['type'] = self.bus_type
        json['addr_width'] = self.addr_width
        json['data_width'] = self.data_width
        json['reset'] = self.bus_reset
        return json

    def returnBusPkgVHDL(self):
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += '\n'

        s += 'package ' + self.bus_type + '_pkg is\n'
        s += '\n\n'

        dataWidthConstant = 'C_' + self.bus_type.upper() + '_DATA_WIDTH'
        addrWidthConstant = 'C_' + self.bus_type.upper() + '_ADDR_WIDTH'
        dataSubType = 't_' + self.bus_type + '_data'
        addrSubType = 't_' + self.bus_type + '_addr'

        par = ''
        par += 'constant ' + dataWidthConstant
        par += ' : natural := ' + str(self.data_width) + ';\n'
        par += 'constant ' + addrWidthConstant
        par += ' : natural := ' + str(self.addr_width) + ';\n'
        par += '\n'
        par += 'subtype ' + dataSubType + ' is std_logic_vector('
        par += dataWidthConstant + '-1 downto 0);\n'
        par += 'subtype ' + addrSubType + ' is std_logic_vector('
        par += addrWidthConstant + '-1 downto 0);\n'
        par += '\n'
        s += indentString(par)

        s += indentString('type t_' + self.bus_type)
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

        s += indentString('type t_' + self.bus_type)
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

        s += 'end ' + self.bus_type + '_pkg;'

        return s


class InvalidBusType(RuntimeError):
    """ @brief Raised when trying to parse an unspecified or unsupported bus type

    """
    def __init__(self, bus_type):
        msg = "Bus type is not valid: " + bus_type
        super().__init__(msg)


class InvalidResetMode(RuntimeError):
    """Documentation for InvalidResetMode

    """
    def __init__(self, reset):
        msg = "Bus reset mode must be either:\n"
        msg += "- 'async' - asynchronous (default)\n"
        msg += "- 'sync'  - synchronous\n"
        msg += "but was: " + reset
        super().__init__(msg)
        
        
