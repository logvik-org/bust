from bust.utils import indent_string
from bust.vhdl import async_process, sync_process, comb_process, comb_process_with_reset


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
            self.reset_active_low = True

        elif self.bus_type == "ipbus":
            self.short_name = "ipb"
            self.in_type = "ipb_wbus"
            self.out_type = "ipb_rbus"
            self.bus_reset = "sync"
            self.reset_active_low = False

        if self.reset_active_low is True:
            if self.bus_reset == "async":
                self.reset_name = "areset_n"
            else:
                self.reset_name = "reset_n "
        else:
            if self.bus_reset == "async":
                self.reset_name = "areset  "
            else:
                self.reset_name = "reset   "

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
        clk_name = self.clk_name
        reset_name = self.reset_name

        s = "library ieee;\n"
        s += "use ieee.std_logic_1164.all;\n"
        s += "use ieee.numeric_std.all;\n"
        s += "\n"
        if self.comp_library != "work":
            s += "library " + self.comp_library + ";\n"
        if self.bus_type == "ipbus":
            s += "use " + self.comp_library + "." + self.bus_type + ".all;\n"
        else:
            s += "use " + self.comp_library + "." + self.bus_type + "_pkg.all;\n"
        s += "use work." + mod.name + "_pif_pkg.all;\n\n"

        s += "entity " + mod.name + "_" + self.short_name + "_pif is\n\n"
        s += indent_string("generic (\n")
        par = "-- " + self.bus_type.upper() + " Bus Interface Generics\n"
        par += (
            "g_"
            + self.short_name
            + "_baseaddr        : std_logic_vector("
            + str(self.addr_width - 1)
        )
        par += " downto 0) := (others => '0'));\n"
        s += indent_string(par, 2)

        s += indent_string("port (")

        par = ""
        if mod.count_rw_regs() + mod.count_ro_regs() + mod.count_pulse_regs() > 0:
            par += "\n-- " + self.bus_type.upper() + " Bus Interface Ports\n"

        if mod.count_rw_regs() > 0:
            par += (
                self.short_name + "_rw_regs    : out t_" + mod.name + "_rw_regs    := "
            )
            par += "c_" + mod.name + "_rw_regs;\n"

        if mod.count_ro_regs() > 0:
            par += (
                self.short_name + "_ro_regs    : in  t_" + mod.name + "_ro_regs    := "
            )
            par += "c_" + mod.name + "_ro_regs;\n"

        if mod.count_pulse_regs() > 0:
            par += (
                self.short_name + "_pulse_regs : out t_" + mod.name + "_pulse_regs := "
            )
            par += "c_" + mod.name + "_pulse_regs;\n"

        par += "\n"
        par += "-- bus signals\n"
        par += clk_name + "            : in  std_logic;\n"
        par += reset_name + "       : in  std_logic;\n"

        # Add bus-specific signals
        if self.bus_type == "axi":

            par += "awaddr         : in  t_" + mod.name + "_addr;\n"
            par += "awvalid        : in  std_logic;\n"
            par += "awready        : out std_logic;\n"
            par += "wdata          : in  t_" + mod.name + "_data;\n"
            par += "wvalid         : in  std_logic;\n"
            par += "wready         : out std_logic;\n"
            par += "bresp          : out std_logic_vector(1 downto 0);\n"
            par += "bvalid         : out std_logic;\n"
            par += "bready         : in  std_logic;\n"
            par += "araddr         : in  t_" + mod.name + "_addr;\n"
            par += "arvalid        : in  std_logic;\n"
            par += "arready        : out std_logic;\n"
            par += "rdata          : out t_" + mod.name + "_data;\n"
            par += "rresp          : out std_logic_vector(1 downto 0);\n"
            par += "rvalid         : out std_logic;\n"
            par += "rready         : in  std_logic\n"

        elif self.bus_type == "ipbus":
            par += "{}_in         : in  {};\n".format(self.short_name, self.in_type)
            par += "{}_out        : out {}\n".format(self.short_name, self.out_type)

        par += ");\n"
        s += indent_string(par, 2)
        s += "end " + mod.name + "_" + self.short_name + "_pif;\n\n"

        s += "architecture behavior of {}_{}_pif is\n\n".format(
            mod.name, self.short_name
        )

        if self.bus_type == "ipbus":
            par = (
                "constant C_BASEADDR : std_logic_vector(31 downto 0) := g_"
                + self.short_name
                + "_baseaddr;\n"
            )
        else:
            par = (
                "constant C_BASEADDR : t_"
                + self.short_name
                + "_addr := g_"
                + self.short_name
                + "_baseaddr;\n"
            )
        s += indent_string(par)

        s += "\n"

        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            par = ""
            par += "-- internal signal for readback" + "\n"
            s += indent_string(par)
            if mod.count_rw_regs() > 0:
                par = "signal " + self.short_name + "_rw_regs_i    : t_"
                par += mod.name + "_rw_regs := c_" + mod.name + "_rw_regs;\n"
                s += indent_string(par)
            if mod.count_pulse_regs() > 0:
                par = "signal " + self.short_name + "_pulse_regs_i : t_"
                par += mod.name + "_pulse_regs := c_" + mod.name + "_pulse_regs;\n"
                s += indent_string(par)
                par = "signal " + self.short_name + "_pulse_regs_cycle : t_"
                par += mod.name + "_pulse_regs := c_" + mod.name + "_pulse_regs;\n"
                s += indent_string(par)

        s += "\n"

        # Add bus-specific logic
        if self.bus_type == "axi":
            s += self.return_axi_pif_VHDL(mod, clk_name, str.strip(reset_name))
        elif self.bus_type == "ipbus":
            s += self.return_ipbus_pif_VHDL(mod, clk_name, str.strip(reset_name))

        return s

    def return_axi_pif_VHDL(self, mod, clk_name, reset_name):
        s = ""
        par = "-- internal bus signals for readback\n"
        par += "signal awaddr_i      : t_" + mod.name + "_addr;\n"
        par += "signal awready_i     : std_logic;\n"
        par += "signal wready_i      : std_logic;\n"
        par += "signal bresp_i       : std_logic_vector(1 downto 0);\n"
        par += "signal bvalid_i      : std_logic;\n"
        par += "signal araddr_i      : t_" + mod.name + "_addr;\n"
        par += "signal arready_i     : std_logic;\n"
        par += "signal rdata_i       : t_" + mod.name + "_data;\n"
        par += "signal rresp_i       : std_logic_vector(1 downto 0);\n"
        par += "signal rvalid_i      : std_logic;\n\n"

        par += "signal slv_reg_rden : std_logic;\n"
        par += "signal slv_reg_wren : std_logic;\n"
        par += "signal reg_data_out : t_" + mod.name + "_data;\n"
        par += "-- signal byte_index   : integer" + "; -- unused\n\n"
        s += indent_string(par)

        s += "begin\n\n"

        if mod.count_rw_regs() > 0:
            s += indent_string("axi_rw_regs <= axi_rw_regs_i") + ";\n"
        if mod.count_pulse_regs() > 0:
            s += indent_string("axi_pulse_regs <= axi_pulse_regs_i") + ";\n"
        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            s += "\n"

        par = ""
        par += "awready <= awready_i;\n"
        par += "wready  <= wready_i;\n"
        par += "bresp   <= bresp_i;\n"
        par += "bvalid  <= bvalid_i;\n"
        par += "arready <= arready_i;\n"
        par += "rdata   <= rdata_i;\n"
        par += "rresp   <= rresp_i;\n"
        par += "rvalid  <= rvalid_i;\n"
        par += "\n"

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
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_awready",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_awready",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        ####################################################################
        # p_awaddr
        ####################################################################
        reset_string = "awaddr_i <= (others => '0');"

        logic_string = "if (awready_i = '0' and awvalid = '1' and wvalid = '1') then\n"
        logic_string += indent_string("awaddr_i <= awaddr;\n")
        logic_string += "end if;"

        if self.bus_reset == "async":
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_awaddr",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_awaddr",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        ####################################################################
        # p_wready
        ####################################################################
        reset_string = "wready_i <= '0';"

        logic_string = "if (wready_i = '0' and awvalid = '1' and wvalid = '1') then\n"
        logic_string += indent_string("wready_i <= '1';\n")
        logic_string += "else\n"
        logic_string += indent_string("wready_i <= '0';\n")
        logic_string += "end if;"

        if self.bus_reset == "async":
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_wready",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_wready",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        s += indent_string(
            "slv_reg_wren <= wready_i and wvalid and awready_i and awvalid;\n"
        )
        s += "\n"

        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            ###################################################################
            # p_mm_select_write
            ###################################################################
            reset_string = "\n"
            if mod.count_rw_regs() > 0:
                reset_string += "axi_rw_regs_i <= c_" + mod.name + "_rw_regs;\n"
            if mod.count_pulse_regs() > 0:
                reset_string += (
                    "axi_pulse_regs_cycle <= c_" + mod.name + "_pulse_regs;\n"
                )

            logic_string = ""
            # create a generator for looping through all pulse regs
            if mod.count_pulse_regs() > 0:
                logic_string += (
                    "\n-- Return PULSE registers to reset value every clock cycle\n"
                )
                logic_string += (
                    "axi_pulse_regs_cycle <= c_" + mod.name + "_pulse_regs;\n\n"
                )

            logic_string += "\nif (slv_reg_wren = '1') then\n\n"

            # create a generator for looping through all rw and pulse regs
            gen = (
                reg for reg in mod.registers if reg.mode == "rw" or reg.mode == "pulse"
            )
            for reg in gen:
                if reg.mode == "rw":
                    sig_name = "axi_rw_regs_i."
                elif reg.mode == "pulse":
                    sig_name = "axi_pulse_regs_cycle."

                par = "if unsigned(awaddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_"
                par += reg.name.upper() + "), " + str(self.addr_width) + ") then\n\n"
                logic_string += indent_string(par, 2)
                par = ""
                if reg.sig_type == "fields":

                    for field in reg.fields:
                        par += sig_name + reg.name + "." + field.name
                        par += " <= wdata("
                        par += field.get_pos_vhdl()
                        par += ");\n"

                elif reg.sig_type == "default":
                    par += sig_name + reg.name + " <= wdata;\n"
                elif reg.sig_type == "slv":
                    par += sig_name + reg.name + " <= wdata("
                    par += str(reg.length - 1) + " downto 0);\n"
                elif reg.sig_type == "sl":
                    par += sig_name + reg.name + " <= wdata(0);\n"

                logic_string += indent_string(par, 3)
                logic_string += indent_string("\nend if;\n", 2)
                logic_string += "\n"

            logic_string += "end if;\n"

            if self.bus_reset == "async":
                s += indent_string(
                    async_process(
                        clk_name,
                        reset_name,
                        "p_mm_select_write",
                        reset_string,
                        logic_string,
                        self.reset_active_low,
                    )
                )

            elif self.bus_reset == "sync":
                s += indent_string(
                    sync_process(
                        clk_name,
                        reset_name,
                        "p_mm_select_write",
                        reset_string,
                        logic_string,
                        self.reset_active_low,
                    )
                )
            s += "\n"

        # Pulse reg process
        # create a generator for looping through all rw and pulse regs
        gen = (reg for reg in mod.registers if reg.mode == "pulse")
        for reg in gen:
            s += indent_string(self.pulse_reg_process(mod, reg))
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
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_write_response",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_write_response",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        ####################################################################
        # p_arready
        ####################################################################
        reset_string = "arready_i <= '0';\n"
        reset_string += "araddr_i  <= (others => '0');"

        logic_string = "if (arready_i = '0' and arvalid = '1') then\n"
        logic_string += indent_string("arready_i <= '1';\n")
        logic_string += indent_string("araddr_i  <= araddr;\n")
        logic_string += "else\n"
        logic_string += indent_string("arready_i <= '0';\n")
        logic_string += "end if;"

        if self.bus_reset == "async":
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_arready",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_arready",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        ####################################################################
        # p_arvalid
        ####################################################################
        reset_string = "rvalid_i <= '0';\n"
        reset_string += 'rresp_i  <= "00";'

        logic_string = (
            "if (arready_i = '1' and arvalid = '1' and rvalid_i = '0') then\n"
        )
        logic_string += indent_string("rvalid_i <= '1';\n")
        logic_string += indent_string('rresp_i  <= "00";\n')
        logic_string += "elsif (rvalid_i = '1' and rready = '1') then\n"
        logic_string += indent_string("rvalid_i <= '0';\n")
        logic_string += "end if;"

        if self.bus_reset == "async":
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_arvalid",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_arvalid",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        s += indent_string("slv_reg_rden <= arready_i and arvalid and ")
        s += "(not rvalid_i);\n"
        s += "\n"

        ####################################################################
        # p_mm_select_read
        ####################################################################
        logic_string = "reg_data_out <= (others => '0');\n\n"

        gen = [reg for reg in mod.registers if reg.mode == "ro" or reg.mode == "rw"]
        for reg in gen:
            par = (
                "if unsigned(araddr_i) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_"
            )
            par += reg.name.upper() + "), " + str(self.addr_width) + ") then\n\n"
            logic_string += par
            par = ""

            if reg.sig_type == "fields":

                for field in reg.fields:
                    par += "reg_data_out("
                    par += field.get_pos_vhdl()

                    if reg.mode == "rw":
                        par += ") <= axi_rw_regs_i."
                    elif reg.mode == "ro":
                        par += ") <= axi_ro_regs."
                    else:
                        raise Exception("Unknown error occurred")
                    par += reg.name + "." + field.name + ";\n"

            elif reg.sig_type == "default":
                par += "reg_data_out <= "
                if reg.mode == "rw":
                    par += "axi_rw_regs_i."
                elif reg.mode == "ro":
                    par += "axi_ro_regs."
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ";\n"

            elif reg.sig_type == "slv":
                par += "reg_data_out("
                par += str(reg.length - 1) + " downto 0) <= "
                if reg.mode == "rw":
                    par += "axi_rw_regs_i."
                elif reg.mode == "ro":
                    par += "axi_ro_regs."
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ";\n"

            elif reg.sig_type == "sl":
                par += "reg_data_out(0) <= "
                if reg.mode == "rw":
                    par += "axi_rw_regs_i."
                elif reg.mode == "ro":
                    par += "axi_ro_regs."
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ";\n"

            logic_string += indent_string(par)
            logic_string += "\nend if;\n"
            logic_string += "\n"

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
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_output",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_output",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )
        s += "\n"

        s += "end behavior;"
        s += "\n"

        return s

    def return_ipbus_pif_VHDL(self, mod, clk_name, reset_name):
        s = ""
        par = (
            "signal ipb_out_i      : ipb_rbus;\n"
            "signal reg_rden       : std_logic := '0';\n"
            "signal reg_wren       : std_logic := '0';\n"
            "signal wr_ack, rd_ack : std_logic := '0';\n"
            "signal wr_err, rd_err : std_logic := '0';\n"
            "signal ack_d          : std_logic := '0';\n"
        )

        if mod.has_stall_regs():
            par += (
                "signal wr_stall_ack   : std_logic := '0';\n"
                "signal rd_stall_ack   : std_logic := '0';\n"
                "signal stall          : std_logic := '0';\n"
            )

        par += "signal reg_data_out   : t_{}_data;\n\n".format(mod.name)

        s += indent_string(par)

        s += "begin\n\n"

        s += indent_string("ipb_out <= ipb_out_i;\n")
        if mod.count_rw_regs() > 0:
            s += indent_string("ipb_rw_regs <= ipb_rw_regs_i") + ";\n"
        if mod.count_pulse_regs() > 0:
            s += indent_string("ipb_pulse_regs <= ipb_pulse_regs_i") + ";\n"
        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            s += "\n"

        if mod.has_stall_regs():
            s += indent_string(
                "reg_wren <= (ipb_in.ipb_strobe and ipb_in.ipb_write) and not (wr_ack or wr_err or ipb_out_i.ipb_ack or ipb_out_i.ipb_err or wr_stall_ack or stall);\n\n"
            )
        else:
            s += indent_string(
                "reg_wren <= (ipb_in.ipb_strobe and ipb_in.ipb_write) and not (wr_ack or wr_err or ipb_out_i.ipb_ack or ipb_out_i.ipb_err);\n\n"
            )

        if mod.count_rw_regs() + mod.count_pulse_regs() > 0:
            ###################################################################
            # p_write
            ###################################################################
            reset_string = "\n"
            if mod.count_rw_regs() > 0:
                reset_string += "ipb_rw_regs_i <= c_" + mod.name + "_rw_regs;\n"
            if mod.count_pulse_regs() > 0:
                reset_string += (
                    "ipb_pulse_regs_cycle <= c_" + mod.name + "_pulse_regs;\n"
                )
            reset_string += "wr_ack <= '0';\n" "wr_err <= '0';\n"

            logic_string = ""
            # create a generator for looping through all pulse regs
            if mod.count_pulse_regs() > 0:
                logic_string += (
                    "\n-- Return PULSE registers to reset value every clock cycle\n"
                )
                logic_string += (
                    "ipb_pulse_regs_cycle <= c_" + mod.name + "_pulse_regs;\n\n"
                )

            logic_string += "wr_ack <= '0';\n" "wr_err <= '0';\n"
            if mod.has_stall_regs():
                logic_string += "wr_stall_ack <= '0';\n"

            logic_string += "\nif (reg_wren) then\n\n"

            # create a generator for looping through all rw and pulse regs
            gen = (
                reg for reg in mod.registers if reg.mode == "rw" or reg.mode == "pulse"
            )
            for i, reg in enumerate(gen):
                if reg.mode == "rw":
                    sig_name = "ipb_rw_regs_i."
                elif reg.mode == "pulse":
                    sig_name = "ipb_pulse_regs_cycle."

                if i == 0:
                    par = "if"
                else:
                    par = "elsif"
                par += " unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_"
                par += reg.name.upper() + "), " + str(self.addr_width) + ") then\n\n"
                logic_string += indent_string(par)
                par = ""
                if reg.sig_type == "fields":

                    for field in reg.fields:
                        par += sig_name + reg.name + "." + field.name
                        par += " <= ipb_in.ipb_wdata("
                        par += field.get_pos_vhdl()
                        par += ");\n"

                elif reg.sig_type == "default":
                    par += sig_name + reg.name + " <= ipb_in.ipb_wdata;\n"
                elif reg.sig_type == "slv":
                    par += sig_name + reg.name + " <= ipb_in.ipb_wdata("
                    par += str(reg.length - 1) + " downto 0);\n"
                elif reg.sig_type == "sl":
                    par += sig_name + reg.name + " <= ipb_in.ipb_wdata(0);\n"
                if reg.stall:
                    par += "wr_stall_ack <= '1';\n"
                else:
                    par += "wr_ack <= '1';\n"

                logic_string += indent_string(par, 2)
                logic_string += "\n"

            logic_string += indent_string("else\n\n")
            logic_string += indent_string("wr_err <= '1';\n\n", 2)

            logic_string += indent_string("end if;\n")
            logic_string += "end if;\n"

            if self.bus_reset == "async":
                s += indent_string(
                    async_process(
                        clk_name,
                        reset_name,
                        "p_write",
                        reset_string,
                        logic_string,
                        self.reset_active_low,
                    )
                )

            elif self.bus_reset == "sync":
                s += indent_string(
                    sync_process(
                        clk_name,
                        reset_name,
                        "p_write",
                        reset_string,
                        logic_string,
                        self.reset_active_low,
                    )
                )
            s += "\n"

        # Pulse reg process
        # create a generator for looping through all rw and pulse regs
        gen = (reg for reg in mod.registers if reg.mode == "pulse")
        for reg in gen:
            s += indent_string(self.pulse_reg_process(mod, reg))
            s += "\n"

        if mod.has_stall_regs():
            s += indent_string(
                "\nreg_rden <= (ipb_in.ipb_strobe and (not ipb_in.ipb_write)) and not (rd_ack or rd_err or ipb_out_i.ipb_ack or ipb_out_i.ipb_err or rd_stall_ack or stall);\n\n"
            )
        else:
            s += indent_string(
                "\nreg_rden <= (ipb_in.ipb_strobe and (not ipb_in.ipb_write)) and not (rd_ack or rd_err or ipb_out_i.ipb_ack or ipb_out_i.ipb_err);\n\n"
            )

        ####################################################################
        # p_read
        ####################################################################
        reset_string = (
            "reg_data_out <= (others => '0');\n" "rd_ack <= '0';\n" "rd_err <= '0';"
        )

        logic_string = "\n-- default values\n" "rd_ack <= '0';\n" "rd_err <= '0';\n"
        if mod.has_stall_regs():
            logic_string += "rd_stall_ack <= '0';\n"

        logic_string += "\nif (reg_rden) then\n"
        logic_string += indent_string("reg_data_out <= (others => '0');\n\n")

        gen = [reg for reg in mod.registers if reg.mode == "ro" or reg.mode == "rw"]
        for i, reg in enumerate(gen):
            if i == 0:
                par = "if"
            else:
                par = "elsif"
            par += " unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_"
            par += reg.name.upper() + "), " + str(self.addr_width) + ") then\n\n"
            logic_string += indent_string(par)
            par = ""

            if reg.sig_type == "fields":

                for field in reg.fields:
                    par += "reg_data_out("
                    par += field.get_pos_vhdl()

                    if reg.mode == "rw":
                        par += ") <= ipb_rw_regs_i."
                    elif reg.mode == "ro":
                        par += ") <= ipb_ro_regs."
                    else:
                        raise Exception("Unknown error occurred")
                    par += reg.name + "." + field.name + ";\n"

            elif reg.sig_type == "default":
                par += "reg_data_out <= "
                if reg.mode == "rw":
                    par += "ipb_rw_regs_i."
                elif reg.mode == "ro":
                    par += "ipb_ro_regs."
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ";\n"

            elif reg.sig_type == "slv":
                par += "reg_data_out("
                par += str(reg.length - 1) + " downto 0) <= "
                if reg.mode == "rw":
                    par += "ipb_rw_regs_i."
                elif reg.mode == "ro":
                    par += "ipb_ro_regs."
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ";\n"

            elif reg.sig_type == "sl":
                par += "reg_data_out(0) <= "
                if reg.mode == "rw":
                    par += "ipb_rw_regs_i."
                elif reg.mode == "ro":
                    par += "ipb_ro_regs."
                else:
                    raise Exception("Unknown error occurred")
                par += reg.name + ";\n"
            if reg.stall:
                par += "rd_stall_ack <= '1';\n"
            else:
                par += "rd_ack <= '1';\n"

            logic_string += indent_string(par, 2)
            logic_string += "\n"

        logic_string += indent_string("else\n\n")
        logic_string += indent_string('reg_data_out <= 32X"DEADBEEF";\n', 2)
        logic_string += indent_string("rd_err <= '1';\n\n", 2)

        logic_string += indent_string("end if;\n")
        logic_string += "end if;\n"

        if self.bus_reset == "async":
            s += indent_string(
                async_process(
                    clk_name,
                    reset_name,
                    "p_read",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        elif self.bus_reset == "sync":
            s += indent_string(
                sync_process(
                    clk_name,
                    reset_name,
                    "p_read",
                    reset_string,
                    logic_string,
                    self.reset_active_low,
                )
            )

        s += "\n"

        ####################################################################
        # p_stall
        ####################################################################
        if mod.has_stall_regs():
            variables = ["v_cnt : natural := 0"]
            reset_string = "stall <= '0';"

            logic_string = "ack_d <= '0';\n" "if wr_stall_ack or rd_stall_ack then\n"
            logic_string += indent_string("stall <= '1';\n")
            gen = [reg for reg in mod.registers if reg.stall]
            for reg in gen:
                logic_string += indent_string(
                    "if unsigned(ipb_in.ipb_addr) = resize(unsigned(C_BASEADDR) + unsigned(C_ADDR_{}), {}) then\n".format(
                        reg.name.upper(), str(self.addr_width)
                    )
                )
                logic_string += indent_string(
                    "v_cnt := {};\n".format(reg.get_stall_cycles_str()), 2
                )
                logic_string += indent_string("end if;\n")

            logic_string += "elsif v_cnt > 0 then\n"
            logic_string += indent_string("v_cnt := v_cnt - 1;\n")
            logic_string += indent_string("stall <= '1';\n")
            logic_string += "elsif stall then\n"
            logic_string += indent_string("stall <= '0';\n")
            logic_string += indent_string("ack_d <= '1';\n")
            logic_string += "end if;\n"

            if self.bus_reset == "async":
                s += indent_string(
                    async_process(
                        clk_name,
                        reset_name,
                        "p_stall",
                        reset_string,
                        logic_string,
                        self.reset_active_low,
                        variables,
                    )
                )

            elif self.bus_reset == "sync":
                s += indent_string(
                    sync_process(
                        clk_name,
                        reset_name,
                        "p_stall",
                        reset_string,
                        logic_string,
                        self.reset_active_low,
                        variables,
                    )
                )
            s += "\n"

        ####################################################################
        # p_output
        ####################################################################
        reset_string = (
            "ipb_out_i.ipb_rdata <= (others => '0');\n"
            "ipb_out_i.ipb_ack <= '0';\n"
            "ipb_out_i.ipb_err <= '0';"
        )

        logic_string = (
            "ipb_out_i.ipb_rdata <= reg_data_out;\n"
            "ipb_out_i.ipb_ack <= '0';\n"
            "ipb_out_i.ipb_err <= '0';\n\n"
        )
        if mod.has_stall_regs():
            logic_string += "if (rd_ack or rd_err) and (not stall) then\n"
        else:
            logic_string += "if (rd_ack or rd_err) then\n"
        logic_string += indent_string("ipb_out_i.ipb_ack <= rd_ack;\n")
        logic_string += indent_string("ipb_out_i.ipb_err <= rd_err;\n")
        if mod.has_stall_regs():
            logic_string += "elsif (wr_ack or wr_err) and (not stall) then\n"
        else:
            logic_string += "elsif (wr_ack or wr_err) then\n"
        logic_string += indent_string("ipb_out_i.ipb_ack <= wr_ack;\n")
        logic_string += indent_string("ipb_out_i.ipb_err <= wr_err;\n")
        if mod.has_stall_regs():
            logic_string += "elsif ack_d then\n"
            logic_string += indent_string("ipb_out_i.ipb_ack <= ack_d;\n")
        logic_string += "end if;\n"

        s += indent_string(
            comb_process_with_reset(
                reset_name,
                "p_output",
                reset_string,
                logic_string,
                self.reset_active_low,
            )
        )

        s += "\n"

        s += "end behavior;"
        s += "\n"

        return s

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
        logic_string += "end if;\n"
        return sync_process(
            clk_name,
            reset_name,
            proc_name,
            reset_string,
            logic_string,
            self.reset_active_low,
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
                "axilite_bfm_config.clock_period <= C_CLK_PERIOD;\n"
                "axilite_bfm_config.setup_time   <= C_CLK_PERIOD/8;\n"
                "axilite_bfm_config.hold_time    <= C_CLK_PERIOD/8;\n\n"
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
