from jinja2 import Environment, FileSystemLoader
import os

from bust.utils import indent_string
from bust.vhdl_gen import comb_process_with_reset
from bust.vhdl_gen import (
    _seq_process_async_reset,
    comb_process,
    _seq_process_sync_reset,
    seq_process,
)
from bust.jinja_utils.filters import indent_all


class BusVHDLGen:
    def __init__(
        self,
        bus_type,
        comp_library,
        data_width,
        addr_width,
    ):
        """Code generator for the Bus module."""
        self.bus_type = bus_type
        self.comp_library = comp_library
        self.clk_name = "clk"
        self.data_width = data_width
        self.addr_width = addr_width

        if self.bus_type == "axi":
            self.short_name = "axi"
            self.in_type = "t_axi_mosi"
            self.out_type = "t_axi_miso"
            self.bus_reset = "async"
            self.reset_active_high = False
            self.reset_async = True

        elif self.bus_type == "ipbus":
            self.short_name = "ipb"
            self.in_type = "ipb_wbus"
            self.out_type = "ipb_rbus"
            self.bus_reset = "sync"
            self.reset_active_high = True
            self.reset_async = False

        if self.reset_active_high:
            if self.bus_reset == "async":
                self.reset_name = "areset  "
            else:
                self.reset_name = "reset   "
        else:
            if self.bus_reset == "async":
                self.reset_name = "areset_n"
            else:
                self.reset_name = "reset_n "

    def return_bus_pkg_VHDL(self):
        if self.bus_type == "axi":

            s = "library ieee;\n"
            s += "use ieee.std_logic_1164.all;\n"
            s += "\n"

            s += "package " + self.bus_type + "_pkg is\n"
            s += "\n\n"

            data_width_constant = "C_" + self.bus_type.upper() + "_DATA_WIDTH"
            addr_width_constant = "C_" + self.bus_type.upper() + "_ADDR_WIDTH"
            data_sub_type = "t_" + self.bus_type + "_data"
            addr_sub_type = "t_" + self.bus_type + "_addr"

            par = ""
            par += "constant " + data_width_constant
            par += " : natural := " + str(self.data_width) + ";\n"
            par += "constant " + addr_width_constant
            par += " : natural := " + str(self.addr_width) + ";\n"
            par += "\n"
            par += "subtype " + data_sub_type + " is std_logic_vector("
            par += data_width_constant + "-1 downto 0);\n"
            par += "subtype " + addr_sub_type + " is std_logic_vector("
            par += addr_width_constant + "-1 downto 0);\n"
            par += "\n"
            s += indent_string(par)

            s += indent_string("type t_" + self.bus_type)
            s += "_mosi is record\n"
            par = ""
            par += "araddr  : " + addr_sub_type + ";\n"
            par += "arvalid : std_logic;\n"
            par += "awaddr  : " + addr_sub_type + ";\n"
            par += "awvalid : std_logic;\n"
            par += "bready  : std_logic;\n"
            par += "rready  : std_logic;\n"
            par += "wdata   : " + data_sub_type + ";\n"
            par += "wvalid  : std_logic;\n"
            s += indent_string(par, 2)
            s += indent_string("end record;\n")
            s += "\n"

            s += indent_string("type t_" + self.bus_type)
            s += "_miso is record\n"
            par = ""
            par += "arready : std_logic;\n"
            par += "awready : std_logic;\n"
            par += "bresp   : std_logic_vector(1 downto 0);\n"
            par += "bvalid  : std_logic;\n"
            par += "rdata   : " + data_sub_type + ";\n"
            par += "rresp   : std_logic_vector(1 downto 0);\n"
            par += "rvalid  : std_logic;\n"
            par += "wready  : std_logic;\n"
            s += indent_string(par, 2)
            s += indent_string("end record;\n")
            s += "\n"

            s += "end " + self.bus_type + "_pkg;"
            s += "\n"

        return s

    def return_bus_pif_VHDL(self, mod):
        # Set up Jinja2 environment
        template_dir = os.path.join(os.path.dirname(__file__), "templates")

        env = Environment(
            loader=FileSystemLoader(template_dir, followlinks=True),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        env.filters["indent_all"] = indent_all

        # Load the IPBus-specific module template
        template = env.get_template("vhdl/module/pif.j2")

        # Define context for template rendering
        context = {
            "module": mod,
            "bus": mod.bus,  # Assumes `module` has an attribute `bus`
            "NL": "\n",  # Ensures newline formatting if needed
        }
        return template.render(context)

    def get_instantiation(self, name, inter):

        if self.bus_type == "axi":
            s = "awaddr              => " + self.short_name + "_in.awaddr(C_"
            s += name.upper() + "_ADDR_WIDTH-1 downto 0),\n"
            s += "awvalid             => " + self.short_name + "_in.awvalid,\n"
            s += (
                "awready             => "
                + self.short_name
                + "_out{0}.awready,\n".format(inter)
            )
            s += "wdata               => " + self.short_name + "_in.wdata(C_"
            s += name.upper() + "_DATA_WIDTH-1 downto 0),\n"
            s += "wvalid              => " + self.short_name + "_in.wvalid,\n"
            s += (
                "wready              => "
                + self.short_name
                + "_out{0}.wready,\n".format(inter)
            )
            s += (
                "bresp               => "
                + self.short_name
                + "_out{0}.bresp,\n".format(inter)
            )
            s += (
                "bvalid              => "
                + self.short_name
                + "_out{0}.bvalid,\n".format(inter)
            )
            s += "bready              => " + self.short_name + "_in.bready,\n"
            s += "araddr              => " + self.short_name + "_in.araddr(C_"
            s += name.upper() + "_ADDR_WIDTH-1 downto 0),\n"
            s += "arvalid             => " + self.short_name + "_in.arvalid,\n"
            s += (
                "arready             => "
                + self.short_name
                + "_out{0}.arready,\n".format(inter)
            )
            s += (
                "rdata               => "
                + self.short_name
                + "_out{0}.rdata(C_".format(inter)
            )
            s += name.upper() + "_DATA_WIDTH-1 downto 0),\n"
            s += (
                "rresp               => "
                + self.short_name
                + "_out{0}.rresp,\n".format(inter)
            )
            s += (
                "rvalid              => "
                + self.short_name
                + "_out{0}.rvalid,\n".format(inter)
            )
            s += "rready              => " + self.short_name + "_in.rready\n"
        elif self.bus_type == "ipbus":
            s = "ipb_in              => ipb_in,\n"
            s += "ipb_out             => ipb_out{}\n".format(inter)

        return s

    def pulse_reg_process(self, mod, reg):

        clk_name = self.clk_name
        reset_name = str.strip(self.reset_name)
        proc_name = "p_pulse_" + reg.name
        const_name = "c_" + mod.name + "_pulse_regs." + reg.name
        reg_name = self.short_name + "_pulse_regs_i." + reg.name
        reg_tmp_name = self.short_name + "_pulse_regs_cycle." + reg.name
        if reg.pulse_cycles > 1:
            variables = [
                "cnt : natural range 0 to " + str(reg.pulse_cycles - 1) + " := 0"
            ]
        else:
            variables = []

        reset_string = reg_name + " <= " + const_name + ";"

        logic_string = "if " + reg_tmp_name
        logic_string += " /= " + const_name
        logic_string += " then\n"

        par = ""
        if reg.pulse_cycles > 1:
            par = "cnt := " + str(reg.pulse_cycles - 1) + ";\n"
        par += reg_name + " <= " + reg_tmp_name + ";\n"
        logic_string += indent_string(par)

        logic_string += "else\n"
        if reg.pulse_cycles > 1:
            logic_string += indent_string("if cnt > 0 then\n")
            logic_string += indent_string("cnt := cnt - 1;\n", 2)
            logic_string += indent_string("else\n")

        par = reg_name + " <= " + const_name + ";\n"
        if reg.pulse_cycles > 1:
            logic_string += indent_string(par, 2)
        else:
            logic_string += indent_string(par, 1)
        if reg.pulse_cycles > 1:
            logic_string += indent_string("end if;\n")
        logic_string += "end if;"
        return _seq_process_sync_reset(
            proc_name,
            clk_name,
            logic_string,
            reset_name,
            reset_string,
            self.reset_active_high,
            variables,
        )

    def get_uvvm_lib(self):
        if self.bus_type == "axi":
            s = (
                "library bitvis_vip_axilite;\n"
                "use bitvis_vip_axilite.axilite_bfm_pkg.all;\n"
            )
        elif self.bus_type == "ipbus":
            s = "library vip_ipbus;\n" "use vip_ipbus.ipbus_bfm_pkg.all;\n"
        return s

    def get_uvvm_signals(self):
        s = ""
        if self.bus_type == "axi":
            s += "-- Bitvis UVVM AXILITE BFM\n"
        elif self.bus_type == "ipbus":
            s += "-- vip_ipbus BFM\n"

        s += (
            "constant data_width : natural := {};\n"
            "constant addr_width : natural := {};\n"
            ""
        ).format(self.data_width, self.addr_width)

        if self.bus_type == "axi":
            s += (
                "signal axilite_if : t_axilite_if(write_address_channel(awaddr(addr_width -1 downto 0)),\n"
                "                                 write_data_channel(wdata(data_width -1 downto 0),\n"
                "                                                    wstrb((data_width/8) -1 downto 0)),\n"
                "                                 read_address_channel(araddr(addr_width -1 downto 0)),\n"
                "                                 read_data_channel(rdata(data_width -1 downto 0))) "
                ":= init_axilite_if_signals(data_width, addr_width);\n"
            )
            s += "signal axilite_bfm_config : t_axilite_bfm_config := C_AXILITE_BFM_CONFIG_DEFAULT;\n\n"
            s += (
                "-- Unused AXILITE signals\n"
                "signal dummy_arprot : std_logic_vector(2 downto 0);\n"
                "signal dummy_awprot : std_logic_vector(2 downto 0);\n"
                "signal dummy_wstrb  : std_logic_vector((data_width/8)-1 downto 0);\n"
            )

        elif self.bus_type == "ipbus":
            s += (
                "signal ipbus_if : t_ipbus_if := init_ipbus_if_signals;\n"
                "signal ipbus_bfm_config : t_ipbus_bfm_config := C_IPBUS_BFM_CONFIG_DEFAULT;\n"
            )

        return s

    def get_uvvm_signal_assignment(self):
        s = ""
        if self.bus_type == "axi":
            s = (
                "axilite_bfm_config.clock_period      <= C_CLK_PERIOD;\n"
                "axilite_bfm_config.setup_time        <= C_CLK_PERIOD/8;\n"
                "axilite_bfm_config.hold_time         <= C_CLK_PERIOD/8;\n"
                "axilite_bfm_config.num_b_pipe_stages <= 0;\n\n"
                "axi_in.araddr  <= axilite_if.read_address_channel.araddr;\n"
                "dummy_arprot   <= axilite_if.read_address_channel.arprot;\n"
                "axi_in.arvalid <= axilite_if.read_address_channel.arvalid;\n"
                "axi_in.awaddr  <= axilite_if.write_address_channel.awaddr;\n"
                "dummy_awprot   <= axilite_if.write_address_channel.awprot;\n"
                "axi_in.awvalid <= axilite_if.write_address_channel.awvalid;\n"
                "axi_in.bready  <= axilite_if.write_response_channel.bready;\n"
                "axi_in.rready  <= axilite_if.read_data_channel.rready;\n"
                "axi_in.wdata   <= axilite_if.write_data_channel.wdata;\n"
                "dummy_wstrb    <= axilite_if.write_data_channel.wstrb;\n"
                "axi_in.wvalid  <= axilite_if.write_data_channel.wvalid;\n\n"
                "axilite_if.read_address_channel.arready  <= axi_out.arready;\n"
                "axilite_if.write_address_channel.awready <= axi_out.awready;\n"
                "axilite_if.write_response_channel.bresp  <= axi_out.bresp;\n"
                "axilite_if.write_response_channel.bvalid <= axi_out.bvalid;\n"
                "axilite_if.read_data_channel.rdata       <= axi_out.rdata;\n"
                "axilite_if.read_data_channel.rresp       <= axi_out.rresp;\n"
                "axilite_if.read_data_channel.rvalid      <= axi_out.rvalid;\n"
                "axilite_if.write_data_channel.wready     <= axi_out.wready;\n"
            )
        elif self.bus_type == "ipbus":
            s = (
                "ipbus_bfm_config.clock_period    <= C_CLK_PERIOD;\n"
                "ipbus_bfm_config.setup_time      <= C_CLK_PERIOD/8;\n"
                "ipbus_bfm_config.hold_time       <= C_CLK_PERIOD/8;\n"
                "ipbus_bfm_config.max_wait_cycles <= 256;\n\n"
                "ipb_in.ipb_wdata  <= ipbus_if.wdata;\n"
                "ipb_in.ipb_write  <= ipbus_if.wr;\n"
                "ipb_in.ipb_addr  <= ipbus_if.addr;\n"
                "ipb_in.ipb_strobe  <= ipbus_if.strobe;\n\n"
                "ipbus_if.rdata  <= ipb_out.ipb_rdata;\n"
                "ipbus_if.ack  <= ipb_out.ipb_ack;\n"
                "ipbus_if.err  <= ipb_out.ipb_err;\n"
            )

        return s

    def get_uvvm_overloads(self):
        s = ""
        if self.bus_type == "axi":
            ext_name = "axilite"
        elif self.bus_type == "ipbus":
            ext_name = self.bus_type

        s += (
            "procedure write(\n"
            "  constant addr_value : in unsigned;\n"
            "  constant data_value : in std_logic_vector;\n"
            "  constant msg        : in string) is\n"
            "begin\n"
            "  {0}_write(addr_value,\n"
            "                data_value,\n"
            "                msg,\n"
            "                {1}_{2},\n"
            "                {0}_if,\n"
            "                C_SCOPE,\n"
            "                shared_msg_id_panel,\n"
            "                {0}_bfm_config);\n"
            "end;\n\n"
        ).format(ext_name, self.short_name, self.clk_name)

        s += (
            "procedure read(\n"
            "  constant addr_value : in  unsigned;\n"
            "  variable data_value : out std_logic_vector;\n"
            "  constant msg        : in  string) is\n"
            "begin\n"
            "  {0}_read(addr_value,\n"
            "               data_value,\n"
            "               msg,\n"
            "               {1}_{2},\n"
            "               {0}_if,\n"
            "               C_SCOPE,\n"
            "               shared_msg_id_panel,\n"
            "               {0}_bfm_config);\n"
            "end;\n"
        ).format(ext_name, self.short_name, self.clk_name)
        s += "variable dummy_data : std_logic_vector(31 downto 0);\n\n"

        s += (
            "procedure check(\n"
            "  constant addr_value : in unsigned;\n"
            "  constant data_exp   : in std_logic_vector;\n"
            "  constant msg        : in string) is\n"
            "begin\n"
            "  {0}_check(addr_value,\n"
            "                data_exp,\n"
            "                msg,\n"
            "                {1}_{2},\n"
            "                {0}_if,\n"
            "                error,\n"
            "                C_SCOPE,\n"
            "                shared_msg_id_panel,\n"
            "                {0}_bfm_config);\n"
            "end;\n\n"
        ).format(ext_name, self.short_name, self.clk_name)

        return s

    def uvvm_write(self, reg_addr, value, string):
        s = 'write(f_addr(g_{}_baseaddr, {}), {}, "{}");\n'.format(
            self.short_name, reg_addr, value, string
        )
        return s

    def uvvm_check(self, reg_addr, data_exp, string):
        s = 'check(f_addr(g_{}_baseaddr, {}), {}, "{}");\n'.format(
            self.short_name, reg_addr, data_exp, string
        )
        return s
