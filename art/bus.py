from utils import indentString


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
