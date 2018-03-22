from collections import OrderedDict

from uart.utils import indent_string
from uart.vhdl import async_process
from uart.vhdl import comb_process
from uart.vhdl import sync_process

class Bus(object):
    """! @brief Managing bus information

    """
    supported_bus = ['axi']

    def __init__(self, bus):
        if bus['type'] in Bus.supported_bus:
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

        # Temporarily force all resets to be active_low
        self.reset_active_low = True

    def get_clk_name(self):
        return "clk"

    def get_reset_name(self):
        if self.bus_reset == "async":
            reset_name = "areset"
        else:
            reset_name = "reset"

        if self.reset_active_low is True:
            reset_name += "_n"

        return reset_name

    def return_JSON(self):
        json = OrderedDict()
        json['type'] = self.bus_type
        json['addr_width'] = self.addr_width
        json['data_width'] = self.data_width
        json['reset'] = self.bus_reset
        return json

    def return_bus_pkg_VHDL(self):
        
        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += '\n'

        s += 'package ' + self.bus_type + '_pkg is\n'
        s += '\n\n'

        data_width_constant = 'C_' + self.bus_type.upper() + '_DATA_WIDTH'
        addr_width_constant = 'C_' + self.bus_type.upper() + '_ADDR_WIDTH'
        data_sub_type = 't_' + self.bus_type + '_data'
        addr_sub_type = 't_' + self.bus_type + '_addr'

        par = ''
        par += 'constant ' + data_width_constant
        par += ' : natural := ' + str(self.data_width) + ';\n'
        par += 'constant ' + addr_width_constant
        par += ' : natural := ' + str(self.addr_width) + ';\n'
        par += '\n'
        par += 'subtype ' + data_sub_type + ' is std_logic_vector('
        par += data_width_constant + '-1 downto 0);\n'
        par += 'subtype ' + addr_sub_type + ' is std_logic_vector('
        par += addr_width_constant + '-1 downto 0);\n'
        par += '\n'
        s += indent_string(par)

        s += indent_string('type t_' + self.bus_type)
        s += '_interconnect_to_slave is record\n'
        par = ''
        par += 'araddr  : ' + addr_sub_type + ';\n'
        par += 'arprot  : std_logic_vector(2 downto 0);\n'
        par += 'arvalid : std_logic;\n'
        par += 'awaddr  : ' + addr_sub_type + ';\n'
        par += 'awprot  : std_logic_vector(2 downto 0);\n'
        par += 'awvalid : std_logic;\n'
        par += 'bready  : std_logic;\n'
        par += 'rready  : std_logic;\n'
        par += 'wdata   : ' + data_sub_type + ';\n'
        par += 'wstrb   : std_logic_vector((' + data_width_constant
        par += '/8)-1 downto 0);\n'
        par += 'wvalid  : std_logic;\n'
        s += indent_string(par, 2)
        s += indent_string('end record;\n')
        s += '\n'

        s += indent_string('type t_' + self.bus_type)
        s += '_slave_to_interconnect is record\n'
        par = ''
        par += 'arready : std_logic;\n'
        par += 'awready : std_logic;\n'
        par += 'bresp   : std_logic_vector(1 downto 0);\n'
        par += 'bvalid  : std_logic;\n'
        par += 'rdata   : ' + data_sub_type + ';\n'
        par += 'rresp   : std_logic_vector(1 downto 0);\n'
        par += 'rvalid  : std_logic;\n'
        par += 'wready  : std_logic;\n'
        s += indent_string(par, 2)
        s += indent_string('end record;\n')
        s += '\n'

        s += 'end ' + self.bus_type + '_pkg;'

        return s

    def return_bus_pif_VHDL(self, mod):
        clk_name = self.get_clk_name()
        reset_name = self.get_reset_name()

        s = 'library ieee;\n'
        s += 'use ieee.std_logic_1164.all;\n'
        s += 'use ieee.numeric_std.all;\n'
        s += '\n'
        s += 'use work.' + mod.name + '_pif_pkg.all;\n\n'
        s += 'entity ' + mod.name + '_' + self.bus_type + '_pif is\n\n'

        s += indent_string('port (')

        par = ''
        if mod.count_rw_regs() + mod.count_ro_regs() + mod.count_pulse_regs() > 0:
            par += '\n-- register record signals\n'

        if mod.count_rw_regs() > 0:
            par += self.bus_type + '_rw_regs : out t_' + mod.name + '_rw_regs := '
            par += 'c_' + mod.name + '_rw_regs;\n'

        if mod.count_ro_regs() > 0:
            par += self.bus_type + '_ro_regs : in  t_' + mod.name + '_ro_regs := '
            par += 'c_' + mod.name + '_ro_regs;\n'

        if mod.count_pulse_regs() > 0:
            par += self.bus_type + '_pulse_regs : out t_' + mod.name + '_pulse_regs := '
            par += 'c_' + mod.name + '_pulse_regs;\n'
            
        
        par += '\n'
        par += '-- bus signals\n'
        par += clk_name + '            : in  std_logic;\n'
        par += reset_name + '       : in  std_logic;\n'

        # Add bus-specific signals
        if self.bus_type == 'axi':
            
            par += 'awaddr         : in  t_' + mod.name + '_addr;\n'
            par += 'awvalid        : in  std_logic;\n'
            par += 'awready        : out std_logic;\n'
            par += 'wdata          : in  t_' + mod.name + '_data;\n'
            par += 'wvalid         : in  std_logic;\n'
            par += 'wready         : out std_logic;\n'
            par += 'bresp          : out std_logic_vector(1 downto 0);\n'
            par += 'bvalid         : out std_logic;\n'
            par += 'bready         : in  std_logic;\n'
            par += 'araddr         : in  t_' + mod.name + '_addr;\n'
            par += 'arvalid        : in  std_logic;\n'
            par += 'arready        : out std_logic;\n'
            par += 'rdata          : out t_' + mod.name + '_data;\n'
            par += 'rresp          : out std_logic_vector(1 downto 0);\n'
            par += 'rvalid         : out std_logic;\n'
            par += 'rready         : in  std_logic\n'
            par += ');\n'
            s += indent_string(par, 2)

        s += 'end ' + mod.name + '_' + self.bus_type + '_pif;\n\n'

        s += 'architecture behavior of ' + mod.name + '_axi_pif is\n\n'

        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            par = ''
            par += '-- internal signal for readback' + '\n'
            s += indent_string(par)
            if mod.count_rw_regs() > 0:
                par = 'signal ' + self.bus_type + '_rw_regs_i : t_'
                par += mod.name + '_rw_regs := c_' + mod.name + '_rw_regs;\n'
                s += indent_string(par)
            if mod.count_pulse_regs() > 0:
                par = 'signal ' + self.bus_type + '_pulse_regs_i : t_'
                par += mod.name + '_pulse_regs := c_' + mod.name + '_pulse_regs;\n'
                s += indent_string(par)
            s += '\n'
        

        # Add bus-specific logic
        if self.bus_type == 'axi':

            s += self.return_axi_pif_VHDL(mod, clk_name, reset_name)

        else:
            raise Exception("Bus type " + self.bus_type + " is not supported...")

        return s

    def return_axi_pif_VHDL(self, mod, clk_name, reset_name):
        s = ''
        par = '-- internal bus signals for readback\n'
        par += 'signal awaddr_i      : t_' + mod.name + '_addr;\n'
        par += 'signal awready_i     : std_logic;\n'
        par += 'signal wready_i      : std_logic;\n'
        par += 'signal bresp_i       : std_logic_vector(1 downto 0);\n'
        par += 'signal bvalid_i      : std_logic;\n'
        par += 'signal araddr_i      : t_' + mod.name + '_addr;\n'
        par += 'signal arready_i     : std_logic;\n'
        par += 'signal rdata_i       : t_' + mod.name + '_data;\n'
        par += 'signal rresp_i       : std_logic_vector(1 downto 0);\n'
        par += 'signal rvalid_i      : std_logic;\n\n'

        par += 'signal slv_reg_rden : std_logic;\n'
        par += 'signal slv_reg_wren : std_logic;\n'
        par += 'signal reg_data_out : t_' + mod.name + '_data;\n'
        par += '-- signal byte_index   : integer' + '; -- unused\n\n'
        s += indent_string(par)

        s += 'begin\n\n'

        if mod.count_rw_regs() > 0:
            s += indent_string('axi_rw_regs <= axi_rw_regs_i') + ';\n'
        if mod.count_pulse_regs() > 0:
            s += indent_string('axi_pulse_regs <= axi_pulse_regs_i') + ';\n'
        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
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

        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_awready", reset_string,
                                             logic_string, self.reset_active_low))

        elif self.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_awready", reset_string,
                                            logic_string, self.reset_active_low))
        s += "\n"
        
        ####################################################################
        # p_awaddr
        ####################################################################
        reset_string = "awaddr_i <= (others => '0');"

        logic_string = "if (awready_i = '0' and awvalid = '1' and wvalid = '1') then\n"
        logic_string += indent_string("awaddr_i <= awaddr;\n")
        logic_string += "end if;"

        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_awaddr", reset_string, logic_string))

        elif self.bus_reset == "sync":
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

        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_wready", reset_string, logic_string))

        elif self.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_wready", reset_string, logic_string))
        s += "\n"

        s += indent_string('slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;\n')
        s += '\n'

        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            ###################################################################
            # p_mm_select_write
            ###################################################################
            reset_string = ""
            if mod.count_rw_regs() > 0:
                reset_string += '\naxi_rw_regs_i <= c_' + mod.name + '_rw_regs;\n'
            if mod.count_pulse_regs() > 0:
                reset_string += '\naxi_pulse_regs_i <= c_' + mod.name + '_pulse_regs;\n'

            logic_string = ""
            # create a generator for looping through all pulse regs
            if mod.count_pulse_regs() > 0:
                logic_string += "\n-- Return PULSE registers to reset value every clock cycle\n"
                logic_string += 'axi_pulse_regs_i <= c_' + mod.name + '_pulse_regs;\n\n'

            logic_string += "\nif (slv_reg_wren = '1') then\n"
            logic_string += indent_string('case awaddr_i is\n\n')

            # create a generator for looping through all rw and pulse regs
            gen = (reg for reg in mod.registers if reg.mode == "rw" or reg.mode == "pulse")
            for reg in gen:
                if reg.mode == 'rw':
                    sig_name = 'axi_rw_regs_i.'
                elif reg.mode == 'pulse':
                    sig_name = 'axi_pulse_regs_i.'
            
                logic_string += indent_string('when C_ADDR_', 2)
                logic_string += reg.name.upper() + ' =>\n\n'
                par = ''
                if reg.sig_type == 'fields':

                    for field in reg.fields:
                        par += sig_name + reg.name + '.' + field.name
                        par += ' <= wdata('
                        par += field.get_pos_vhdl()
                        par += ');\n'

                elif reg.sig_type == 'default':
                    par += sig_name + reg.name + ' <= wdata;\n'
                elif reg.sig_type == 'slv':
                    par += sig_name + reg.name + ' <= wdata('
                    par += str(reg.length - 1) + ' downto 0);\n'
                elif reg.sig_type == 'sl':
                    par += sig_name + reg.name + ' <= wdata(0);\n'

                logic_string += indent_string(par, 3)
                logic_string += '\n'

            logic_string += indent_string('when others =>\n', 2)
            logic_string += indent_string('null;\n', 3)
            logic_string += '\n'
            logic_string += indent_string('end case;\n')
            logic_string += 'end if;\n'

            if self.bus_reset == "async":
                s += indent_string(async_process(clk_name, reset_name, "p_mm_select_write",
                                                 reset_string, logic_string))

            elif self.bus_reset == "sync":
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
        
        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_write_response",
                                             reset_string, logic_string))

        elif self.bus_reset == "sync":
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

        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_arready",
                                             reset_string, logic_string))

        elif self.bus_reset == "sync":
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

        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_arvalid",
                                             reset_string, logic_string))

        elif self.bus_reset == "sync":
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

        gen = [reg for reg in mod.registers
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

        if self.bus_reset == "async":
            s += indent_string(async_process(clk_name, reset_name, "p_output", reset_string,
                                             logic_string, self.reset_active_low))

        elif self.bus_reset == "sync":
            s += indent_string(sync_process(clk_name, reset_name, "p_output", reset_string,
                                            logic_string, self.reset_active_low))
        s += "\n"

        s += 'end behavior;'

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
        
        
