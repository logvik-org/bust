from utils import indent_string
from utils import add_line_breaks
from exceptions import InvalidAddress
from exceptions import InvalidRegister

from register import Register

from vhdl import sync_process
from vhdl import async_process
from vhdl import comb_process

import json
from collections import OrderedDict


class Module:
    """! @brief Managing module information


    """

    def __init__(self, mod, bus):
        """! @brief
        """
        self.bus = bus
        self.registers = []
        self.addresses = []
        self.name = mod['name']
        self.addr_width = mod['addr_width']
        self.data_width = mod['data_width']
        self.description = add_line_breaks(mod['description'], 25)
        if 'baseaddr' in mod:
            self.baseaddr = int(mod['baseaddr'], 16)
        else:
            self.baseaddr = 0
        for reg in mod['register']:
            self.add_register(reg)

    def add_register(self, reg):
        if self.register_valid(reg):
            if "address" in reg:
                addr = int(reg['address'], 16)
                if self.is_address_free(addr):
                    self.is_address_out_of_range(addr)
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

    def return_bus_pif_VHDL(self):
        clk_name = self.bus.get_clk_name()
        reset_name = self.bus.get_reset_name()

        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += 'use work.' + self.name + '_pif_pkg.all;\n\n'
        s += 'entity ' + self.name + '_' + self.bus.bus_type + '_pif is\n\n'

        s += indent_string('port (')

        par = ''
        par += '\n-- register record signals\n'
        par += 'axi_ro_regs : in  t_' + self.name + '_ro_regs := '
        par += 'c_' + self.name + '_ro_regs;\n'
        par += 'axi_rw_regs : out t_' + self.name + '_rw_regs := '
        par += 'c_' + self.name + '_rw_regs;\n'
        par += '\n'
        par += '-- bus signals\n'
        par += clk_name + '         : in  std_logic;\n'
        par += reset_name + '    : in  std_logic;\n'
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
        s += indent_string(par, 2)

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
        s += indent_string(par)

        s += 'begin\n\n'
        s += indent_string('axi_rw_regs <= axi_rw_regs_i') + ';\n'
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

        s += indent_string(par)

        ####################################################################
        # p_awready
        ####################################################################
        reset_string = "awready_i <= '0';"

        logic_string = "if (awready_i = '0' and awvalid = '1'  and wvalid = '1') then\n"
        logic_string += indent_string("awready_i <= '1';\n")
        logic_string += "else\n"
        logic_string += indent_string("awready_i <= '0';\n")
        logic_string += "end if;"

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_awready", reset_string,
                                             logic_string, self.bus.reset_active_low))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_awready", reset_string,
                                            logic_string, self.bus.reset_active_low))
        s += "\n"
        
        ####################################################################
        # p_awaddr
        ####################################################################
        reset_string = "awaddr_i <= (others => '0');"

        logic_string = "if (awready_i = '0' and awvalid = '1' and wvalid = '1') then\n"
        logic_string += indent_string("awaddr_i <= awaddr;\n")
        logic_string += "end if;"

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_awaddr", reset_string, logic_string))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_awaddr", reset_string, logic_string))
        s += "\n"

        ####################################################################
        # p_wready
        ####################################################################
        reset_string = "wready_i <= '0';"

        logic_string = "if (wready_i = '0' and awvalid = '1' and wvalid = '1') then\n"
        logic_string += indent_string("wready_i <= '1';\n")
        logic_string += 'else\n'
        logic_string += indent_string("wready_i <= '0';\n")
        logic_string += "end if;"

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_wready", reset_string, logic_string))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_wready", reset_string, logic_string))
        s += "\n"

        s += indent_string('slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;\n')
        s += '\n'

        ###################################################################
        # p_mm_select_write
        ###################################################################
        reset_string = '\naxi_rw_regs_i <= c_' + self.name + '_rw_regs;\n'

        logic_string = "\nif (slv_reg_wren = '1') then\n"
        logic_string += indent_string('case awaddr_i is\n\n')
        
        # create a generator for looping through all rw regs
        gen = (reg for reg in self.registers if reg.mode == "rw")
        for reg in gen:
            logic_string += indent_string('when C_ADDR_', 2)
            logic_string += reg.name.upper() + ' =>\n\n'
            par = ''
            if reg.sig_type == 'fields':

                for field in reg.fields:
                    par += 'axi_rw_regs_i.' + reg.name + '.' + field.name
                    par += ' <= wdata('
                    par += field.get_pos_vhdl()
                    par += ');\n'

            elif reg.sig_type == 'default':
                par += 'axi_rw_regs_i.' + reg.name + ' <= wdata;\n'
            elif reg.sig_type == 'slv':
                par += 'axi_rw_regs_i.' + reg.name + ' <= wdata('
                par += str(reg.length - 1) + ' downto 0);\n'
            elif reg.sig_type == 'sl':
                par += 'axi_rw_regs_i.' + reg.name + ' <= wdata(0);\n'

            logic_string += indent_string(par, 3)
            logic_string += '\n'

        logic_string += indent_string('when others =>\n', 2)
        logic_string += indent_string('null;\n', 3)
        logic_string += '\n'
        logic_string += indent_string('end case;\n')
        logic_string += 'end if;\n'

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_mm_select_write",
                                             reset_string, logic_string))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_mm_select_write",
                                            reset_string, logic_string))
        s += "\n"

        ####################################################################
        # p_write_response
        ####################################################################
        reset_string = "bvalid_i <= '0';\n"
        reset_string += 'bresp_i  <= "00";'

        logic_string = "if (awready_i = '1' and awvalid = '1' and wready_i = '1' "
        logic_string += "and wvalid = '1' and bvalid_i = '0') then\n"
        logic_string += indent_string("bvalid_i <= '1';\n")
        logic_string += indent_string('bresp_i  <= "00";\n')
        logic_string += "elsif (bready = '1' and bvalid_i = '1') then\n"
        logic_string += indent_string("bvalid_i <= '0';\n")
        logic_string += "end if;"
        
        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_write_response",
                                             reset_string, logic_string))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_write_response",
                                            reset_string, logic_string))
        s += "\n"

        ####################################################################
        # p_arready
        ####################################################################
        reset_string = "arready_i <= '0';\n"
        reset_string += "araddr_i  <= (others => '0');"

        logic_string = "if (arready_i = '0' and arvalid = '1') then\n"
        logic_string += indent_string("arready_i <= '1';\n")
        logic_string += indent_string('araddr_i  <= araddr;\n')
        logic_string += 'else\n'
        logic_string += indent_string("arready_i <= '0';\n")
        logic_string += "end if;"

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_arready",
                                             reset_string, logic_string))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_arready",
                                            reset_string, logic_string))
        s += "\n"

        ####################################################################
        # p_arvalid
        ####################################################################
        reset_string = "rvalid_i <= '0';\n"
        reset_string += 'rresp_i  <= "00";'

        logic_string = "if (arready_i = '1' and arvalid = '1' and rvalid_i = '0') then\n"
        logic_string += indent_string("rvalid_i <= '1';\n")
        logic_string += indent_string('rresp_i  <= "00";\n')
        logic_string += "elsif (rvalid_i = '1' and rready = '1') then\n"
        logic_string += indent_string("rvalid_i <= '0';\n")
        logic_string += "end if;"

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_arvalid",
                                             reset_string, logic_string))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_arvalid",
                                            reset_string, logic_string))
        s += "\n"


        s += indent_string('slv_reg_rden <= arready_i and arvalid and ')
        s += '(not rvalid_i);\n'
        s += '\n'

        ####################################################################
        # p_mm_select_read
        ####################################################################
        logic_string = "reg_data_out <= (others => '0');\n\n"
        logic_string += 'case araddr_i is\n\n'

        gen = [reg for reg in self.registers
               if reg.mode == "ro" or reg.mode == "rw"]
        for reg in gen:
            logic_string += indent_string('when C_ADDR_')
            logic_string += reg.name.upper() + ' =>\n\n'
            par = ''

            if reg.sig_type == 'fields':

                for field in reg.fields:
                    par += 'reg_data_out('
                    par += field.get_pos_vhdl()

                    if reg.mode == 'rw':
                        par += ') <= axi_rw_regs_i.'
                    elif reg.mode == 'ro':
                        par += ') <= axi_ro_regs.'
                    else:
                        raise Exception("Unknown error occurred")
                    par += reg.name + '.' + field.name + ';\n'

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

            logic_string += indent_string(par, 2)
            logic_string += '\n'

        logic_string += indent_string('when others =>\n')
        logic_string += indent_string('null;\n', 2)
        logic_string += '\n'
        logic_string += 'end case;\n'

        s += indent_string(comb_process("p_mm_select_read", logic_string))
        s += "\n"

        ####################################################################
        # p_output
        ####################################################################
        reset_string = "rdata_i <= (others => '0');"

        logic_string = "if (slv_reg_rden = '1') then\n"
        logic_string += indent_string("rdata_i <= reg_data_out;\n")
        logic_string += "end if;"

        if self.bus.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_output", reset_string,
                                             logic_string, self.bus.reset_active_low))

        elif self.bus.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_output", reset_string,
                                            logic_string, self.bus.reset_active_low))
        s += "\n"

        s += 'end behavior;'

        return s

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

        s += indent_string('signal ' + self.bus.bus_type + '_rw_regs : t_')
        s += self.name + '_rw_regs := c_' + self.name + '_rw_regs;\n'
        s += indent_string('signal ' + self.bus.bus_type + '_ro_regs : t_')
        s += self.name + '_ro_regs := c_' + self.name + '_ro_regs;\n'

        s += '\n'

        s += 'begin\n'
        s += '\n'

        s += indent_string('i_' + self.name + '_' + self.bus.bus_type + '_pif ')
        s += ': entity work.' + self.name + '_' + self.bus.bus_type + '_pif\n'
        s += indent_string('port map (\n', 2)

        par = ''
        par += self.bus.bus_type + '_ro_regs => ' + self.bus.bus_type + '_ro_regs,\n'
        par += self.bus.bus_type + '_rw_regs => ' + self.bus.bus_type + '_rw_regs,\n'
        par += self.bus.get_clk_name() + '         => ' + self.bus.bus_type + '_' + self.bus.get_clk_name() + ',\n'
        par += self.bus.get_reset_name() + '    => ' + self.bus.bus_type + '_' + self.bus.get_reset_name()  + 'areset_n,\n'
        par += 'awaddr      => ' + self.bus.bus_type + '_in.awaddr(C_'
        par += self.name.upper() + '_ADDR_WIDTH-1 downto 0),\n'
        par += 'awvalid     => ' + self.bus.bus_type + '_in.awvalid,\n'
        par += 'awready     => ' + self.bus.bus_type + '_out.awready,\n'
        par += 'wdata       => ' + self.bus.bus_type + '_in.wdata(C_'
        par += self.name.upper() + '_DATA_WIDTH-1 downto 0),\n'
        par += 'wvalid      => ' + self.bus.bus_type + '_in.wvalid,\n'
        par += 'wready      => ' + self.bus.bus_type + '_out.wready,\n'
        par += 'bresp       => ' + self.bus.bus_type + '_out.bresp,\n'
        par += 'bvalid      => ' + self.bus.bus_type + '_out.bvalid,\n'
        par += 'bready      => ' + self.bus.bus_type + '_in.bready,\n'
        par += 'araddr      => ' + self.bus.bus_type + '_in.araddr(C_'
        par += self.name.upper() + '_ADDR_WIDTH-1 downto 0),\n'
        par += 'arvalid     => ' + self.bus.bus_type + '_in.arvalid,\n'
        par += 'arready     => ' + self.bus.bus_type + '_out.arready,\n'
        par += 'rdata       => ' + self.bus.bus_type + '_out.rdata(C_'
        par += self.name.upper() + '_DATA_WIDTH-1 downto 0),\n'
        par += 'rresp       => ' + self.bus.bus_type + '_out.rresp,\n'
        par += 'rvalid      => ' + self.bus.bus_type + '_out.rvalid,\n'
        par += 'rready      => ' + self.bus.bus_type + '_in.rready\n'
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
            self.is_address_out_of_range(addr)
            if self.is_address_free(addr):
                self.addresses.append(addr)
                return addr
            else:
                # force integer division to prevent float
                addr += self.data_width // 8

    def is_address_out_of_range(self, addr):
        if addr > pow(2, self.addr_width) - 1:
            raise RuntimeError("Address " + hex(addr) +
                               " is definetely out of range...")
        return True

    def is_address_free(self, addr):
        for address in self.addresses:
            if address == addr:
                return False
        # If loop completes without matching addresses
        return True

    def update_addresses(self):
        self.addresses = []
        for reg in self.registers:
            addr = self.get_next_address()
            self.addresses.append(addr)
            reg.address = addr
            

    def register_valid(self, reg):
        if set(("name", "mode", "type", "description")).issubset(reg):
            return True
        elif set(("name", "mode", "fields", "description")).issubset(reg):
            return True
        else:
            return False

    def __str__(self):
        string = "Name: " + self.name + "\n"
        string += "Address width: " + str(self.addr_width) + "\n"
        string += "Data width: " + str(self.data_width) + "\n"
        string += "Description: " + self.description + "\n\n"
        string += "Registers: \n"
        for i, reg in enumerate(self.registers):
            string += indent_string(str(reg), 1)
        return string


