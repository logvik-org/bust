"""@package module
Contains the Module class and relevant exceptions

"""

import json
from collections import OrderedDict

from uart.utils import indent_string
from uart.utils import add_line_breaks
from uart.exceptions import InvalidAddress
from uart.exceptions import InvalidRegister
from uart.register import Register
from uart.vhdl import is_valid_VHDL
from uart.vhdl import is_unique


class Module:
    """! @brief Managing module information

    Contain the name of the module, the bus type and addr and data width specification +
    description of the module.
    """

    def __init__(self, mod, bus):
        """! @brief
        """
        try:
            self.bus = bus
            self.registers = []
            self.addresses = []
            
            is_valid_VHDL(mod['name'])
            self.name = mod['name']
            self.addr_width = mod['addr_width']
            self.data_width = mod['data_width']
            self.description = mod['description']
            self.description_with_breaks = add_line_breaks(mod['description'], 25)
            if 'baseaddr' in mod:
                self.baseaddr = int(mod['baseaddr'], 16)
            else:
                self.baseaddr = 0
            for reg in mod['register']:
                self.add_register(reg)

        except Exception as e:
            print(e)
            exit(2)

    def add_register(self, reg):
        if self.register_valid(reg):
            if "address" in reg:
                addr = int(reg['address'], 16)
                if self.is_address_free(addr):
                    if self.is_address_out_of_range(addr):
                        raise RuntimeError("Address " + hex(addr) +
                               " is definetely out of range...")
                    self.addresses.append(addr)
                    self.registers.append(Register(reg, addr, self.data_width))
                else:
                    raise InvalidAddress(reg['name'], addr)
            else:
                addr = self.get_next_address()
                self.addresses.append(addr)
                self.registers.append(Register(reg, addr, self.data_width))
        else:
            raise InvalidRegister(reg)

    def return_module_pkg_VHDL(self):
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += "package " + self.name + "_pif_pkg is"
        s += "\n\n"

        par = ''
        par += "constant C_" + self.name.upper()
        par += "_ADDR_WIDTH : natural := " + str(self.addr_width) + ";\n"
        par += "constant C_" + self.name.upper()
        par += "_DATA_WIDTH : natural := " + str(self.data_width) + ";\n"
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
            par += " : t_" + self.name + "_addr := " + str(self.addr_width)
            par += 'X"' + '%X' % reg.address + '";\n'
        par += '\n'
        s += indent_string(par)

        if self.count_rw_regs() > 0:
            s += indent_string("-- RW Register Record Definitions\n\n")

            # Create all types for RW registers with records
            for reg in self.registers:
                if reg.mode == "rw" and reg.sig_type == "fields":
                    s += indent_string("type t_" + self.name + "_rw_")
                    s += reg.name + " is record\n"

                    for field in reg.fields:
                        s += indent_string(field.name, 2) + " : "
                        if field.sig_type == "slv":
                            s += "std_logic_vector(" + str(field.length - 1)
                            s += " downto 0);\n"
                        elif field.sig_type == "sl":
                            s += "std_logic;\n"
                        else:
                            raise RuntimeError(
                                "Something went wrong..." + field.sig_type)
                    s += indent_string("end record;\n\n")

            # The RW register record type
            s += indent_string("type t_" + self.name + "_rw_regs is record\n")
            for reg in self.registers:
                if reg.mode == "rw":
                    s += indent_string(reg.name, 2) + " : "
                    if reg.sig_type == "default" or (reg.sig_type == "slv" and reg.length == self.data_width):
                        s += "t_" + self.name + "_data;\n"
                    elif reg.sig_type == "slv":
                        s += "std_logic_vector(" + \
                            str(reg.length - 1) + " downto 0);\n"
                    elif reg.sig_type == "sl":
                        s += "std_logic;\n"
                    elif reg.sig_type == "fields":
                        s += "t_" + self.name + "_rw_" + reg.name + ";\n"
                    else:
                        raise RuntimeError("Something went wrong...")
            s += indent_string("end record;\n")
            s += "\n"

            s += indent_string("-- RW Register Reset Value Constant\n\n")

            s += indent_string("constant c_") + self.name + "_rw_regs : t_"
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

                elif reg.sig_type == 'fields':

                    if len(reg.fields) > 1:
                        par += '(\n'
                    else:
                        par += '('

                    for j, field in enumerate(reg.fields):
                        if len(reg.fields) > 1:
                            par += indent_string(field.name + ' => ')
                        else:
                            par += field.name + ' => '

                        if field.sig_type == 'slv':

                            if field.reset == "0x0":
                                par += "(others => '0')"
                            else:
                                par += str(field.length) + 'X"'
                                par += format(int(field.reset, 16), 'X') + '"'

                        elif field.sig_type == 'sl':
                            par += "'" + format(int(field.reset, 16), 'X') + "'"

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

                s += indent_string(par, 2)
            s += '\n'

        if self.count_ro_regs() > 0:

            s += indent_string("-- RO Register Record Definitions\n\n")

            # Create all types for RO registers with records
            for reg in self.registers:
                if reg.mode == "ro" and reg.sig_type == "fields":
                    s += indent_string("type t_" + self.name + "_ro_")
                    s += reg.name + " is record\n"

                    for field in reg.fields:
                        s += indent_string(field.name, 2) + " : "
                        if field.sig_type == "slv":
                            s += "std_logic_vector(" + str(field.length - 1)
                            s += " downto 0);\n"
                        elif field.sig_type == "sl":
                            s += "std_logic;\n"
                        else:
                            raise RuntimeError("Something went wrong...")
                    s += indent_string("end record;\n\n")

            # The RO register record type
            s += indent_string("type t_" + self.name + "_ro_regs is record\n")
            for reg in self.registers:
                if reg.mode == "ro":
                    s += indent_string(reg.name, 2) + " : "
                    if reg.sig_type == "default" or (reg.sig_type == "slv" and reg.length == self.data_width):
                        s += "t_" + self.name + "_data;\n"
                    elif reg.sig_type == "slv":
                        s += "std_logic_vector(" + \
                            str(reg.length - 1) + " downto 0);\n"
                    elif reg.sig_type == "sl":
                        s += "std_logic;\n"
                    elif reg.sig_type == "fields":
                        s += "t_" + self.name + "_ro_" + reg.name + ";\n"
                    else:
                        raise RuntimeError(
                            "Something went wrong... What now?" + reg.sig_type)
            s += indent_string("end record;\n")
            s += "\n"

            s += indent_string("-- RO Register Reset Value Constant\n\n")

            s += indent_string("constant c_") + self.name + "_ro_regs : t_"
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

                elif reg.sig_type == 'fields':
                    if len(reg.fields) > 1:
                        par += '(\n'
                    else:
                        par += '('

                    for j, field in enumerate(reg.fields):
                        if len(reg.fields) > 1:
                            par += indent_string(field.name + ' => ')
                        else:
                            par += field.name + ' => '

                        if field.sig_type == 'slv':

                            if field.reset == "0x0":
                                par += "(others => '0')"
                            else:
                                par += str(field.length) + 'X"'
                                par += format(int(field.reset, 16), 'X') + '"'

                        elif field.sig_type == 'sl':
                            par += "'" + format(int(field.reset, 16), 'X') + "'"

                        if j < len(reg.fields) - 1:
                            par += ',\n'

                    par += ')'

                elif reg.sig_type == 'sl':
                    par += "'" + format(int(reg.reset, 16), 'X') + "'"

                else:
                    raise RuntimeError(
                            "Something went wrong... What now?" + reg.sig_type)

                if i < len(gen) - 1:
                    par += ','
                else:
                    par += ');'
                par += '\n'

                s += indent_string(par, 2)

        if self.count_pulse_regs() > 0:
            s += indent_string("-- PULSE Register Record Definitions\n\n")

            # Create all types for PULSE registers with records
            for reg in self.registers:
                if reg.mode == "pulse" and reg.sig_type == "fields":
                    s += indent_string("type t_" + self.name + "_pulse_")
                    s += reg.name + " is record\n"

                    for field in reg.fields:
                        s += indent_string(field.name, 2) + " : "
                        if field.sig_type == "slv":
                            s += "std_logic_vector(" + str(field.length - 1)
                            s += " downto 0);\n"
                        elif field.sig_type == "sl":
                            s += "std_logic;\n"
                        else:
                            raise RuntimeError(
                                "Something went wrong..." + field.sig_type)
                    s += indent_string("end record;\n\n")

            # The PULSE register record type
            s += indent_string("type t_" + self.name + "_pulse_regs is record\n")
            for reg in self.registers:
                if reg.mode == "pulse":
                    s += indent_string(reg.name, 2) + " : "
                    if reg.sig_type == "default" or (reg.sig_type == "slv" and reg.length == self.data_width):
                        s += "t_" + self.name + "_data;\n"
                    elif reg.sig_type == "slv":
                        s += "std_logic_vector(" + \
                            str(reg.length - 1) + " downto 0);\n"
                    elif reg.sig_type == "sl":
                        s += "std_logic;\n"
                    elif reg.sig_type == "fields":
                        s += "t_" + self.name + "_pulse_" + reg.name + ";\n"
                    else:
                        raise RuntimeError("Something went wrong...")
            s += indent_string("end record;\n")
            s += "\n"

            s += indent_string("-- PULSE Register Reset Value Constant\n\n")

            s += indent_string("constant c_") + self.name + "_pulse_regs : t_"
            s += self.name + "_pulse_regs := (\n"
            gen = [reg for reg in self.registers if reg.mode == 'pulse']

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

                elif reg.sig_type == 'fields':

                    if len(reg.fields) > 1:
                        par += '(\n'
                    else:
                        par += '('

                    for j, field in enumerate(reg.fields):
                        if len(reg.fields) > 1:
                            par += indent_string(field.name + ' => ')
                        else:
                            par += field.name + ' => '

                        if field.sig_type == 'slv':

                            if field.reset == "0x0":
                                par += "(others => '0')"
                            else:
                                par += str(field.length) + 'X"'
                                par += format(int(field.reset, 16), 'X') + '"'

                        elif field.sig_type == 'sl':
                            par += "'" + format(int(field.reset, 16), 'X') + "'"

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

                s += indent_string(par, 2)
            s += '\n'
            
        s += '\n'

        s += "end package " + self.name + "_pif_pkg;"

        return s

    def return_module_VHDL(self):
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += 'use work.' + self.bus.bus_type + '_pkg.all;\n'
        s += 'use work.' + self.name + '_pif_pkg.all;\n'
        s += '\n'

        s += 'entity ' + self.name + ' is\n'
        s += '\n'
        s += indent_string('port (\n')
        s += '\n'
        par = ''
        par += '-- ' + self.bus.bus_type.upper() + ' Bus Interface\n'
        par += self.bus.bus_type + '_' + self.bus.get_clk_name() + '      : in  std_logic;\n'
        par += self.bus.bus_type + '_' + self.bus.get_reset_name() + ' : in  std_logic;\n'
        par += self.bus.bus_type + '_in       : in  t_' + \
            self.bus.bus_type + '_interconnect_to_slave;\n'
        par += self.bus.bus_type + '_out      : out t_' + \
            self.bus.bus_type + '_slave_to_interconnect\n'
        par += ');\n'
        s += indent_string(par, 2)
        s += '\n'
        s += 'end entity ' + self.name + ';\n'
        s += '\n'

        s += 'architecture behavior of ' + self.name + ' is\n'
        s += '\n'

        if self.count_rw_regs() > 0:
            s += indent_string('signal ' + self.bus.bus_type + '_rw_regs : t_')
            s += self.name + '_rw_regs := c_' + self.name + '_rw_regs;\n'
        if self.count_ro_regs() > 0:
            s += indent_string('signal ' + self.bus.bus_type + '_ro_regs : t_')
            s += self.name + '_ro_regs := c_' + self.name + '_ro_regs;\n'
        if self.count_pulse_regs() > 0:
            s += indent_string('signal ' + self.bus.bus_type + '_pulse_regs : t_')
            s += self.name + '_pulse_regs := c_' + self.name + '_pulse_regs;\n'

        if self.count_rw_regs() + self.count_ro_regs() + self.count_pulse_regs() > 0:
            s += '\n'

        s += 'begin\n'
        s += '\n'

        s += indent_string('i_' + self.name + '_' + self.bus.bus_type + '_pif ')
        s += ': entity work.' + self.name + '_' + self.bus.bus_type + '_pif\n'
        s += indent_string('port map (\n', 2)

        par = ''
        if self.count_rw_regs() > 0:
            par += self.bus.bus_type + '_rw_regs    => ' + self.bus.bus_type + '_rw_regs,\n'
        if self.count_ro_regs() > 0:
            par += self.bus.bus_type + '_ro_regs    => ' + self.bus.bus_type + '_ro_regs,\n'
        if self.count_pulse_regs() > 0:
            par += self.bus.bus_type + '_pulse_regs => ' + self.bus.bus_type + '_pulse_regs,\n'
            
        par += self.bus.get_clk_name() + '            => ' + self.bus.bus_type + '_' + self.bus.get_clk_name() + ',\n'
        par += self.bus.get_reset_name() + '       => ' + self.bus.bus_type + '_' + self.bus.get_reset_name()  + ',\n'
        par += 'awaddr         => ' + self.bus.bus_type + '_in.awaddr(C_'
        par += self.name.upper() + '_ADDR_WIDTH-1 downto 0),\n'
        par += 'awvalid        => ' + self.bus.bus_type + '_in.awvalid,\n'
        par += 'awready        => ' + self.bus.bus_type + '_out.awready,\n'
        par += 'wdata          => ' + self.bus.bus_type + '_in.wdata(C_'
        par += self.name.upper() + '_DATA_WIDTH-1 downto 0),\n'
        par += 'wvalid         => ' + self.bus.bus_type + '_in.wvalid,\n'
        par += 'wready         => ' + self.bus.bus_type + '_out.wready,\n'
        par += 'bresp          => ' + self.bus.bus_type + '_out.bresp,\n'
        par += 'bvalid         => ' + self.bus.bus_type + '_out.bvalid,\n'
        par += 'bready         => ' + self.bus.bus_type + '_in.bready,\n'
        par += 'araddr         => ' + self.bus.bus_type + '_in.araddr(C_'
        par += self.name.upper() + '_ADDR_WIDTH-1 downto 0),\n'
        par += 'arvalid        => ' + self.bus.bus_type + '_in.arvalid,\n'
        par += 'arready        => ' + self.bus.bus_type + '_out.arready,\n'
        par += 'rdata          => ' + self.bus.bus_type + '_out.rdata(C_'
        par += self.name.upper() + '_DATA_WIDTH-1 downto 0),\n'
        par += 'rresp          => ' + self.bus.bus_type + '_out.rresp,\n'
        par += 'rvalid         => ' + self.bus.bus_type + '_out.rvalid,\n'
        par += 'rready         => ' + self.bus.bus_type + '_in.rready\n'
        par += ');\n'
        s += indent_string(par, 3)

        # If bus data width is larger than module data width, set the unused bits to zero
        if self.bus.data_width > self.data_width:
            s += indent_string('-- Set unused bus data bits to zero\n')
            s += indent_string(self.bus.bus_type +
                              '_out.rdata(C_' + self.bus.bus_type.upper())
            s += '_DATA_WIDTH-1 downto C_' + self.name.upper() + '_DATA_WIDTH)'
            s += " <= (others => '0');\n"

        s += '\n'
        s += 'end architecture behavior;'

        return s

    def print_JSON(self, include_address=False):
        """! @brief Returns JSON string

        """
        dic = OrderedDict()

        dic["name"] = self.name

        dic["bus"] = self.bus.return_JSON()
        
        dic["addr_width"] = self.addr_width
        dic["data_width"] = self.data_width
        dic["baseaddr"] = str(hex(self.baseaddr))

        dic["register"] = []

        for i, reg in enumerate(self.registers):
            reg_dic = OrderedDict()

            reg_dic["name"] = reg.name
            reg_dic["mode"] = reg.mode
            reg_dic["type"] = reg.sig_type

            if include_address:
                reg_dic["address"] = str(hex(reg.address))

            if (reg.sig_type != "default" and reg.sig_type != "fields" and
                    reg.sig_type != "sl"):
                reg_dic["length"] = reg.length

            if reg.sig_type != "fields":
                reg_dic["reset"] = reg.reset

            if reg.sig_type == "fields" and len(reg.fields) > 0:
                reg_dic["fields"] = []
                for field in reg.fields:
                    reg_dic["fields"].append(field.return_dic())

            reg_dic["description"] = reg.description

            dic["register"].append(reg_dic)

        dic["description"] = self.description
        return json.dumps(dic, indent=4)

    def get_next_address(self):
        """! @brief Will get the next address based on the byte-addressed scheme

        """
        addr = 0
        found_addr = False
        while (not found_addr):
            if self.is_address_out_of_range(addr):
                raise RuntimeError("Address " + hex(addr) +
                                   " is definetely out of range...")
            if self.is_address_free(addr):
                self.addresses.append(addr)
                return addr
            else:
                # force integer division to prevent float
                addr += self.data_width // 8

    def is_address_out_of_range(self, addr):
        """ Returns True if address is out of range, False if not"""
        
        if addr > pow(2, self.addr_width) - 1:
            return True
            
        return False

    def is_address_free(self, addr):
        """Returns True if address is not been used in the module, False if it already taken"""
        for address in self.addresses:
            if address == addr:
                return False
        # If loop completes without matching addresses
        return True

    def is_address_byte_based(self, addr):
        """Returns True if address is divisable by number of bytes in module data width"""

        if addr % (self.data_width/8) == 0:
            return True
        else:
            return False

    def update_addresses(self):
        self.addresses = []
        for reg in self.registers:
            addr = self.get_next_address()
            self.addresses.append(addr)
            reg.address = addr

    def register_valid(self, reg):
        """Returns True if register is semi-valid. May raise exceptions which must be catched"""

        # Check if all required register keys exists
        if not (set(("name", "mode", "type", "description")).issubset(reg) or
                set(("name", "mode", "fields", "description")).issubset(reg)):
            return False

        """Check if name is valid VHDL, if not it will raise an exception which must be
        catched in calling function"""
        is_valid_VHDL(reg['name'])

        """Get a list of the currently used reg names and compare the chosen reg names to this list
        If it is already taken it will raise an exception which must be catched in calling function"""
        reg_names = [r.name for r in self.registers]
        is_unique(reg['name'], reg_names)

        return True

    def count_ro_regs(self):
        return len([reg for reg in self.registers if reg.mode == 'ro'])

    def count_rw_regs(self):
        return len([reg for reg in self.registers if reg.mode == 'rw'])

    def count_pulse_regs(self):
        return len([reg for reg in self.registers if reg.mode == 'pulse'])

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + self.description + "\n\n"
        string += "Registers: \n"
        for i, reg in enumerate(self.registers):
            string += indent_string(str(reg), 1)
        return string


