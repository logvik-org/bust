import logging
from bust.utils import indent_string
from bust.bus import Bus


class Testbench(object):
    """Class for generating testbenches and tcl scripts for Model/Questa Sim"""

    def __init__(self, module, bus, settings):
        self.logger = logging.getLogger(__name__)
        self.module = module
        self.bus = bus
        self.settings = settings

    @staticmethod
    def get_addr_func():
        s = (
            "function f_addr (\n"
            "  BASE : std_logic_vector(31 downto 0);\n"
            "  REG  : std_logic_vector(31 downto 0))\n"
            "  return unsigned is\n"
            "  variable tmp : unsigned(31 downto 0);\n"
            "begin  -- function f_addr\n"
            "  tmp := unsigned(BASE);\n"
            "  tmp := tmp + unsigned(REG);\n"
            "  return tmp;\n"
            "end function f_addr;\n"
        )
        return s

    def return_uvvm_component_list(self):
        self.logger.debug("Generating UVVM Component List")
        string = "uvvm_util\n"
        string += "uvvm_vvc_framework\n"
        string += "bitvis_vip_scoreboard"
        if self.bus.bus_type == "axi":
            string += "\nbitvis_vip_axilite"
        string += "\n"
        return string

    def return_tcl_script(self):
        self.logger.debug("Generating TCL Script")
        s = (
            "# Set default error behaviour\n"
            "if {[batch_mode]} {\n"
            "  onerror {abort all; exit -f -code 1}\n"
            "} else {\n"
            "  onerror {abort all}\n"
            "}\n\n"
            "# Shut down running simulation\n"
            "quit -sim\n\n"
            "# Set project paths\n"
        )

        s += 'quietly set {}_path "../"\n'.format(self.module.name)

        s += 'quietly set bus_path "{}"\n'.format(
            self.settings.return_sim_bus_path(self.bus.bus_type)
        )
        s += 'quietly set UVVM_path "{}"\n'.format(self.settings.return_sim_uvvm_path())

        if self.bus.bus_type == "ipbus":
            s += 'quietly set vip_ipbus_path "{}"\n'.format(
                self.settings.return_vip_ipbus_path()
            )

        s += (
            "\n# Compile UVVM Dependencies\n"
            "do $UVVM_path/script/compile_all.do $UVVM_path/script ${0}_path/{1} ${0}_path/"
            "{2}/component_list.txt\n\n".format(
                self.module.name, self.settings.sim_dir, self.settings.script_dir
            )
        )

        s += (
            "# Set vcom args\n"
            'quietly set vcom_args "-pedanticerrors -fsmverbose -quiet -check_synthesis'
        )
        if self.settings.coverage:
            s += " +cover=sbt"
        s += '"\n\n'

        if (
            self.bus.comp_library != Bus.default_comp_library
            or self.bus.bus_type == "ipbus"
        ):
            s += (
                "###########################################################################\n"
                "# Compile bus source files into library\n"
                "###########################################################################\n\n"
                "# Set up library and sim path\n"
                'quietly set lib_name "'
            )
            s += self.bus.comp_library
            s += '"\n'
            if self.bus.bus_type == "ipbus":
                s += 'quietly set bus_sim_path "${}_path/{}"\n\n'.format(
                    self.module.name, self.settings.sim_dir
                )
            else:
                s += 'quietly set bus_sim_path "$bus_path/{}"\n\n'.format(
                    self.settings.sim_dir
                )
            s += (
                "# (Re-)Generate library and Compile source files\n"
                'echo "\\nRe-gen lib and compile $lib_name source\\n"\n'
                "if {{[file exists $bus_sim_path/$lib_name]}} {{\n"
                "  file delete -force $bus_sim_path/$lib_name\n"
                "}}\n\n"
            ).format()

            s += "vlib $bus_sim_path/$lib_name\n"
            s += "vmap $lib_name $bus_sim_path/$lib_name\n\n"

            s += 'quietly set vhdldirectives "-2008 -work $lib_name"\n\n'
            if self.bus.bus_type == "ipbus":
                s += "eval vcom $vcom_args $vhdldirectives $bus_path/components/ipbus_core/firmware/hdl/ipbus_package.vhd\n\n"
                s += "# Compile vip_ipbus Dependencies\n"
                s += "do $vip_ipbus_path/scripts/compile_src.do $vip_ipbus_path $vip_ipbus_path/sim\n"
            else:
                s += "eval vcom $vcom_args $vhdldirectives $bus_path/hdl/{}_pkg.vhd\n".format(
                    self.bus.bus_type
                )

        s += (
            "\n\n###########################################################################\n"
            "# Compile source files into library\n"
            "###########################################################################\n\n"
            "# Set up library and sim path\n"
            'quietly set lib_name "'
        )
        s += self.module.name
        s += '"\n'
        s += 'quietly set {0}_sim_path "${0}_path/{1}"\n\n'.format(
            self.module.name, self.settings.sim_dir
        )

        s += (
            "# (Re-)Generate library and Compile source files\n"
            'echo "\\nRe-gen lib and compile $lib_name source\\n"\n'
            "if {{[file exists ${0}_sim_path/$lib_name]}} {{\n"
            "  file delete -force ${0}_sim_path/$lib_name\n"
            "}}\n\n".format(self.module.name)
        )

        s += "vlib ${}_sim_path/$lib_name\n".format(self.module.name)
        s += "vmap $lib_name ${}_sim_path/$lib_name\n\n".format(self.module.name)

        s += 'quietly set vhdldirectives "-2008 -work $lib_name"\n\n'

        if self.bus.comp_library == Bus.default_comp_library:
            s += "eval vcom $vcom_args $vhdldirectives $bus_path/hdl/{}_pkg.vhd\n".format(
                self.bus.bus_type
            )
        s += (
            "eval vcom $vcom_args $vhdldirectives ${0}_path/hdl/{0}_pif_pkg.vhd\n"
            "eval vcom $vcom_args $vhdldirectives ${0}_path/hdl/{0}_{1}_pif.vhd\n\n"
        ).format(self.module.name, self.bus.short_name)

        s += (
            "###########################################################################\n"
            "# Compile testbench files into library\n"
            "###########################################################################\n"
            'quietly set vcom_args "-quiet"\n'
        )
        s += "eval vcom $vcom_args $vhdldirectives ${0}_path/tb/{0}_{1}_pif_tb.vhd\n\n".format(
            self.module.name, self.bus.short_name
        )

        s += (
            "###########################################################################\n"
            "# Simulate\n"
            "###########################################################################\n"
        )
        s += "vsim -quiet "
        if self.settings.coverage:
            s += "-coverage "
        s += "{0}.{0}_{1}_pif_tb\n\n".format(self.module.name, self.bus.short_name)

        s += (
            "# Trick to avoid metastability warnings\n"
            "quietly set NumericStdNoWarnings 1\n"
            "run 1 ns;\n"
            "quietly set NumericStdNoWarnings 0\n"
            "run -all\n\n"
        )

        if self.settings.coverage:
            if self.bus.bus_type == "axi":
                s += (
                    "coverage exclude -du {0}_{1}_pif -togglenode araddr\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode araddr_i\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode awaddr\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode awaddr_i\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode bresp\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode bresp_i\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode rresp\n"
                    "coverage exclude -du {0}_{1}_pif -togglenode rresp_i\n"
                ).format(self.module.name, self.bus.short_name)
            s += "coverage report\n"
            s += "coverage report -html -htmldir covhtmlreport -code bcefst"

        s += "\n"

        return s

    def return_vhdl_tb(self):
        self.logger.debug("Generating TB Sequencer VHDL")

        s = (
            "library ieee;\n"
            "use ieee.std_logic_1164.all;\n"
            "use ieee.numeric_std.all;\n\n"
        )

        if self.bus.bus_type == "ipbus":
            s += "library ipbus;\n"
            s += "use ipbus.ipbus.all;\n\n"

        else:
            if self.bus.comp_library != Bus.default_comp_library:
                s += "library {};\n".format(self.bus.comp_library)
            s += "use {}.{}_pkg.all;\n".format(self.bus.comp_library, self.bus.bus_type)
        s += "use work.{}_pif_pkg.all;\n\n".format(self.module.name)

        s += "library uvvm_util;\n" "context uvvm_util.uvvm_util_context;\n\n"

        s += self.bus.get_uvvm_lib()

        s += (
            "\n-------------------------------------------------------------------------------\n"
            "\n"
            "entity {0}_{1}_pif_tb is\n"
            "\n"
            "end entity {0}_{1}_pif_tb;\n"
            "\n"
            "-------------------------------------------------------------------------------\n\n"
            ""
        ).format(self.module.name, self.bus.short_name)

        s += "architecture tb of {}_{}_pif_tb is\n\n".format(
            self.module.name, self.bus.short_name
        )

        s += indent_string(
            "constant C_SCOPE      : string := C_TB_SCOPE_DEFAULT;\n"
            "constant C_CLK_PERIOD : time   := 10 ns;\n"
        )
        s += "\n"
        s += indent_string(
            "-- component generics\n"
            'constant g_{}_baseaddr : std_logic_vector(31 downto 0) := 32X"FFAA0000";\n'
            "constant g_instance_num : natural                       := 0;\n"
        ).format(self.bus.short_name)
        s += "\n"

        # Initial reset value
        if self.bus.reset_active_low:
            init_reset = "'1'"
        else:
            init_reset = "'0'"

        s += indent_string("-- component ports\n")
        if self.module.count_rw_regs() > 0:
            s += indent_string(
                "signal {0}_rw_regs    : t_{1}_rw_regs    := c_{1}_rw_regs;\n".format(
                    self.bus.short_name, self.module.name
                )
            )
        if self.module.count_ro_regs() > 0:
            s += indent_string(
                "signal {0}_ro_regs    : t_{1}_ro_regs    := c_{1}_ro_regs;\n".format(
                    self.bus.short_name, self.module.name
                )
            )
        if self.module.count_pulse_regs() > 0:
            s += indent_string(
                "signal {0}_pulse_regs : t_{1}_pulse_regs := c_{1}_pulse_regs;\n".format(
                    self.bus.short_name, self.module.name
                )
            )

        s += indent_string(
            "signal {0}_{2}        : std_logic                   := '1';\n"
            "signal {0}_{3}   : std_logic                   := {4};\n"
            "signal {0}_in         : {5};\n"
            "signal {0}_out        : {6};\n"
            ""
        ).format(
            self.bus.short_name,
            self.module.name,
            self.bus.clk_name,
            self.bus.reset_name,
            init_reset,
            self.bus.in_type,
            self.bus.out_type,
        )
        s += "\n"

        s += indent_string(self.bus.get_uvvm_signals())
        s += "\n"

        s += indent_string(self.get_addr_func())
        s += "\n"

        s += "begin  -- architecture tb\n\n"

        s += indent_string(self.bus.get_uvvm_signal_assignment())
        s += "\n"

        s += indent_string("-- component instantiation\n")
        s += indent_string(self.module.get_instantiation("DUT", False))
        s += "\n"

        s += indent_string(
            ("-- clock generator\n" "clock_generator({}_{}, C_CLK_PERIOD);\n\n").format(
                self.bus.short_name, self.bus.clk_name
            )
        )

        s += indent_string(("-- main testbench\n" "p_main : process\n\n"))

        s += indent_string(self.get_uvvm_gen_overloads(), 2)
        s += indent_string(self.bus.get_uvvm_overloads(), 2)

        s += indent_string("begin\n\n")

        par = (
            "-- enable_log_msg(ALL_MESSAGES);\n"
            "disable_log_msg(ALL_MESSAGES, QUIET);\n"
            "enable_log_msg(ID_LOG_HDR, QUIET);\n"
            "enable_log_msg(ID_LOG_HDR_LARGE, QUIET);\n"
            "enable_log_msg(ID_SEQUENCER, QUIET);\n"
            "-- enable_log_msg(ID_BFM, QUIET);\n"
            "-- enable_log_msg(ID_CLOCK_GEN, QUIET);\n"
            "-- enable_log_msg(ID_GEN_PULSE, QUIET);\n"
            "-- enable_log_msg(ID_POS_ACK, QUIET);\n"
            "\n"
            "-- report_global_ctrl(VOID);\n"
            "-- report_msg_id_panel(VOID);\n"
        )
        s += indent_string(par, 2)

        s += "\n"
        # Initial reset value
        if self.bus.reset_active_low:
            pulse_reset = "'0'"
        else:
            pulse_reset = "'1'"
        par = 'gen_pulse({}_{}, {}, 500 ns, BLOCKING, "Reset for 500 ns");\n'.format(
            self.bus.short_name, str.strip(self.bus.reset_name), pulse_reset
        )

        s += indent_string(par, 2)
        s += "\n"
        for reg in self.module.registers:
            s += indent_string("--\n\n", 2)

            s += indent_string(self.reg_hdr(reg), 2)
            s += "\n"
            s += indent_string(self.check_default_value(reg), 2)
            s += "\n"
            s += indent_string(self.set_check_zero_value(reg), 2)
            s += "\n"
            s += indent_string(self.check_bit_fields(reg), 2)

        if self.bus.bus_type == "ipbus":
            par = (
                "--\n\n"
                'log_hdr_large("Checking that invalid register returns ERR");\n\n'
                "ipbus_bfm_config.expected_response <= ERR;\n\n"
                'log_hdr("Check erroneous read");\n\n'
                'read(32X"FFFFFFFF", dummy_data, "Read from register that does not exist");\n'
                'check_value(dummy_data, 32X"DEADBEEF", error, "Check that the returned data is rubbish");\n\n'
                'log_hdr("Check erroneous write");\n\n'
                'write(32X"FFFFFFFF", 32X"0", "Write to register that does not exist");\n\n'
            )
            s += indent_string(par, 2)

        par = (
            "--==================================================================================================\n"
            "-- Ending the simulation\n"
            "--------------------------------------------------------------------------------------\n"
            "wait for 100 ns;                    -- to allow some time for completion\n"
            "report_alert_counters(FINAL);  -- Report final counters and print conclusion for simulation (Success/Fail)\n"
            'log(ID_LOG_HDR, "SIMULATION COMPLETED", C_SCOPE);\n\n'
            "-- Finish the simulation\n"
            "std.env.stop;\n"
            "wait;                               -- to stop completely\n"
        )
        s += indent_string(par, 2)
        s += indent_string("end process p_main;\n\n")
        s += "end architecture tb;\n"

        return s

    def check_default_value(self, reg):
        s = self.log_hdr("Check Default Value")
        s += "\n"
        msg = "{} default value".format(reg.name)
        signal = "{}_{}_regs.{}".format(self.bus.short_name, reg.mode, reg.name)
        if reg.sig_type in ["sl", "slv", "default"]:
            s += self.check_value(
                signal, self.sig_value(reg.reset, reg.sig_type, reg.length), msg
            )
        elif reg.sig_type == "fields":
            for field in reg.fields:
                msg_field = "{}.{} default value".format(reg.name, field.name)
                signal_field = "{}.{}".format(signal, field.name)
                s += self.check_value(
                    signal_field,
                    self.sig_value(field.reset, field.sig_type, field.length),
                    msg_field,
                )

        if reg.mode in ["rw", "ro"]:
            c_addr = "C_ADDR_{}".format(reg.name.upper())
            exp_value = self.sig_value(reg.reset, "default", reg.length)
            s += self.bus.uvvm_check(c_addr, exp_value, msg)
        elif reg.mode == "pulse":
            pass

        return s

    def set_check_zero_value(self, reg):
        s = self.log_hdr("Set&Check Zero Value")
        s += "\n"
        c_addr = "C_ADDR_{}".format(reg.name.upper())
        signal = "{}_{}_regs.{}".format(self.bus.short_name, reg.mode, reg.name)
        msg = "Setting all bits to zero"
        bus_val = self.sig_value("0", "default")
        if reg.mode == "rw":

            s += self.bus.uvvm_write(c_addr, bus_val, msg)

            if reg.sig_type in ["sl", "slv", "default"]:
                sig_val = self.sig_value("0", reg.sig_type, reg.length)
                s += self.check_value(signal, sig_val, msg)
            elif reg.sig_type == "fields":
                for field in reg.fields:
                    signal_field = "{}.{}".format(signal, field.name)
                    s += self.check_value(
                        signal_field,
                        self.sig_value("0", field.sig_type, field.length),
                        msg,
                    )
            else:
                raise Exception("Invalid register type")

            s += self.bus.uvvm_check(c_addr, bus_val, msg)

        elif reg.mode == "ro":

            if reg.sig_type in ["sl", "slv", "default"]:
                sig_val = self.sig_value("0", reg.sig_type, reg.length)
                s += "{} <= {};\n".format(signal, sig_val)
                s += self.await_value(signal, sig_val, msg)
            elif reg.sig_type == "fields":
                for field in reg.fields:
                    signal_field = "{}.{}".format(signal, field.name)
                    s += "{} <= {};\n".format(
                        signal_field, self.to_zero(field.sig_type)
                    )
                for field in reg.fields:
                    signal_field = "{}.{}".format(signal, field.name)
                    sig_val = self.sig_value("0", field.sig_type, field.length)
                    s += self.await_value(signal_field, sig_val, msg)

            else:
                raise Exception("Invalid register type")

            s += self.bus.uvvm_check(c_addr, bus_val, msg)
        elif reg.mode == "pulse":

            s += self.bus.uvvm_write(c_addr, bus_val, msg)

            if reg.sig_type in ["sl", "slv", "default"]:
                s += self.set_check_zero_pulse(signal, reg, msg)

            elif reg.sig_type == "fields":
                signal_field = list()
                for field in reg.fields:
                    signal_field.append("{}.{}".format(signal, field.name))
                for i, field in enumerate(reg.fields):
                    sig_val = self.sig_value("0", field.sig_type, field.length)
                    s += self.check_value(signal_field[i], sig_val, msg)
                for i, field in enumerate(reg.fields):
                    s += self.await_stable(signal_field[i], reg.pulse_cycles, msg)
                for i, field in enumerate(reg.fields):
                    sig_val = self.sig_value("0", field.sig_type, field.length)
                    s += self.check_value(signal_field[i], sig_val, msg)
                for i, field in enumerate(reg.fields):
                    sig_val = self.sig_value(field.reset, field.sig_type, field.length)
                    s += self.await_value(signal_field[i], sig_val, msg)

            else:
                raise Exception("Invalid register type")

        return s

    def set_check_zero_pulse(self, signal, reg, msg):
        sig_val = self.sig_value("0", reg.sig_type, reg.length)
        s = self.check_value(signal, sig_val, msg)
        s += self.await_stable(signal, reg.pulse_cycles, msg)
        s += self.check_value(signal, sig_val, msg)
        s += self.await_value(
            signal, self.sig_value(reg.reset, reg.sig_type, reg.length), msg
        )
        return s

    def check_bit_fields(self, reg):
        s = ""
        if reg.sig_type in ["sl", "slv", "default"]:
            s += self.log_hdr("Check all bit fields")
            s += "\n"

        c_addr = "C_ADDR_{}".format(reg.name.upper())
        msg = "Check all bit fields"
        signal = "{}_{}_regs.{}".format(self.bus.short_name, reg.mode, reg.name)
        if reg.mode == "rw":
            if reg.sig_type == "sl":
                s += self.check_bit_rw_sl(c_addr, signal, msg)
            elif reg.sig_type in ["slv", "default"]:
                s += self.check_bit_rw_slv(c_addr, signal, reg, msg)
            elif reg.sig_type == "fields":
                for field in reg.fields:
                    signal_field = "{}.{}".format(signal, field.name)
                    s += self.log_hdr("Check all bit fields {}".format(field.name))
                    s += "\n"
                    if field.sig_type == "sl":
                        s += self.check_bit_rw_sl(
                            c_addr, signal_field, msg, field.pos_low
                        )
                    elif field.sig_type in ["slv", "default"]:
                        s += self.check_bit_rw_slv(
                            c_addr, signal_field, field, msg, field.pos_low
                        )
                    s += "\n"
            else:
                raise Exception("Invalid register type")
        elif reg.mode == "ro":
            if reg.sig_type == "sl":
                s += self.check_bit_ro_sl(c_addr, signal, msg)
            elif reg.sig_type in ["slv", "default"]:
                s += self.check_bit_ro_slv(c_addr, signal, reg, msg)
            elif reg.sig_type == "fields":
                for field in reg.fields:
                    signal_field = "{}.{}".format(signal, field.name)
                    s += self.log_hdr("Check all bit fields {}".format(field.name))
                    s += "\n"
                    if field.sig_type == "sl":
                        s += self.check_bit_ro_sl(
                            c_addr, signal_field, msg, field.pos_low
                        )
                    elif field.sig_type in ["slv", "default"]:
                        s += self.check_bit_ro_slv(
                            c_addr, signal_field, field, msg, field.pos_low
                        )
                    s += "\n"
            else:
                raise Exception("Invalid register type")

        elif reg.mode == "pulse":
            if reg.sig_type == "sl":
                s += self.check_bit_pulse_sl(c_addr, signal, reg, msg)
            elif reg.sig_type in ["slv", "default"]:
                s += self.check_bit_pulse_slv(c_addr, signal, reg, msg)
            elif reg.sig_type == "fields":
                for field in reg.fields:
                    signal_field = "{}.{}".format(signal, field.name)
                    s += self.log_hdr("Check all bit fields {}".format(field.name))
                    s += "\n"
                    if field.sig_type == "sl":
                        s += self.check_bit_pulse_sl(
                            c_addr,
                            signal_field,
                            field,
                            msg,
                            field.pos_low,
                            reg.pulse_cycles,
                        )
                    elif field.sig_type in ["slv", "default"]:
                        s += self.check_bit_pulse_slv(
                            c_addr,
                            signal_field,
                            field,
                            msg,
                            field.pos_low,
                            reg.pulse_cycles,
                        )
                    s += "\n"
        # For consistant line endings
        if reg.sig_type != "fields":
            s += "\n"
        return s

    def check_bit_ro_slv(self, c_addr, signal, reg, msg, offset=0):
        s = "for i in 0 to {} loop\n".format(reg.length - 1)
        if offset > 0:
            offset = "+{}".format(offset)
        else:
            offset = ""
        sig_val = "std_logic_vector(to_unsigned(1, {}) sll i)".format(reg.length)
        bus_val = "std_logic_vector(to_unsigned(1, data_width) sll i{})".format(offset)
        par = "{} <= {};\n".format(signal, sig_val)
        par += self.await_value(signal, sig_val, msg)
        par += self.bus.uvvm_check(c_addr, bus_val, msg)
        par += "-- Return to zero\n"
        sig_val = self.sig_value("0", "slv", reg.length)
        bus_val = self.sig_value("0", "default")
        par += "{} <= {};\n".format(signal, sig_val)
        par += self.await_value(signal, sig_val, msg)
        par += self.bus.uvvm_check(c_addr, bus_val, msg)
        s += indent_string(par)
        s += "end loop;\n"
        return s

    def check_bit_rw_slv(self, c_addr, signal, reg, msg, offset=0):
        s = "for i in 0 to {} loop\n".format(reg.length - 1)
        if offset > 0:
            offset = "+{}".format(offset)
        else:
            offset = ""
        sig_val = "std_logic_vector(to_unsigned(1, {}) sll i)".format(reg.length)
        bus_val = "std_logic_vector(to_unsigned(1, data_width) sll i{})".format(offset)
        par = self.bus.uvvm_write(c_addr, bus_val, msg)
        par += self.check_value(signal, sig_val, msg)
        par += self.bus.uvvm_check(c_addr, bus_val, msg)
        par += "-- Return to zero\n"
        sig_val = self.sig_value("0", "slv", reg.length)
        bus_val = self.sig_value("0", "default")
        par += self.bus.uvvm_write(c_addr, bus_val, msg)
        par += self.check_value(signal, sig_val, msg)
        par += self.bus.uvvm_check(c_addr, bus_val, msg)
        s += indent_string(par)
        s += "end loop;\n"
        return s

    def check_bit_pulse_slv(self, c_addr, signal, reg, msg, offset=0, clk_cycles=None):
        if clk_cycles is None:
            clk_cycles = reg.pulse_cycles
        reset = reg.reset
        s = "for i in 0 to {} loop\n".format(reg.length - 1)
        if offset > 0:
            offset = "+{}".format(offset)
        else:
            offset = ""
        sig_val = "std_logic_vector(to_unsigned(1, {}) sll i)".format(reg.length)
        bus_val = "std_logic_vector(to_unsigned(1, data_width) sll i{})".format(offset)
        par = self.bus.uvvm_write(c_addr, bus_val, msg)
        par += self.check_value(signal, sig_val, msg)
        par += self.await_stable(signal, clk_cycles, msg)
        par += self.check_value(signal, sig_val, msg)
        sig_val = self.sig_value(reset, reg.sig_type, reg.length)
        par += self.await_value(signal, sig_val, msg)
        s += indent_string(par)
        s += "end loop;\n"
        return s

    def check_bit_ro_sl(self, c_addr, signal, msg, offset=0):
        sig_val = self.sig_value("1", "sl")
        bus_val = self.sig_value(hex(1 << offset), "default")
        s = "{} <= {};\n".format(signal, sig_val)
        s += self.await_value(signal, sig_val, msg)
        s += self.bus.uvvm_check(c_addr, bus_val, msg)
        s += "-- Return to zero\n"
        sig_val = self.sig_value("0", "sl")
        bus_val = self.sig_value("0", "default")
        s += "{} <= {};\n".format(signal, sig_val)
        s += self.await_value(signal, sig_val, msg)
        s += self.bus.uvvm_check(c_addr, bus_val, msg)
        return s

    def check_bit_rw_sl(self, c_addr, signal, msg, offset=0):
        sig_val = self.sig_value("1", "sl")
        bus_val = self.sig_value(hex(1 << offset), "default")
        s = self.bus.uvvm_write(c_addr, bus_val, msg)
        s += self.check_value(signal, sig_val, msg)
        s += self.bus.uvvm_check(c_addr, bus_val, msg)
        s += "-- Return to zero\n"
        sig_val = self.sig_value("0", "sl")
        bus_val = self.sig_value("0", "default")
        s += self.bus.uvvm_write(c_addr, bus_val, msg)
        s += self.check_value(signal, sig_val, msg)
        s += self.bus.uvvm_check(c_addr, bus_val, msg)
        return s

    def check_bit_pulse_sl(self, c_addr, signal, reg, msg, offset=0, clk_cycles=None):
        if clk_cycles is None:
            clk_cycles = reg.pulse_cycles
        reset = reg.reset
        sig_val = self.sig_value("1", "sl")
        bus_val = self.sig_value(hex(1 << offset), "default")
        s = self.bus.uvvm_write(c_addr, bus_val, msg)
        s += self.check_value(signal, sig_val, msg)
        s += self.await_stable(signal, clk_cycles, msg)
        s += self.check_value(signal, sig_val, msg)
        sig_val = self.sig_value(reset, "sl")
        s += self.await_value(signal, sig_val, msg)
        return s

    def reg_hdr(self, reg):
        if reg.sig_type == "sl":
            reg_type = "std_logic"
        elif reg.sig_type in ["slv", "default"]:
            reg_type = "{} bit std_logic_vector".format(reg.length)
        elif reg.sig_type == "fields":
            reg_type = "fields"
        par = "Checking Register {} - {} {}".format(
            reg.name, reg.mode.upper(), reg_type
        )
        return self.log_hdr_large(par)

    @staticmethod
    def get_uvvm_gen_overloads():
        s = (
            "-- Overloads for convenience\n"
            "procedure log_hdr (\n"
            "  constant msg : in string) is\n"
            "begin  -- procedure log_hdr\n"
            "  log(ID_LOG_HDR, msg, C_SCOPE);\n"
            "end procedure log_hdr;\n\n"
        )

        s += (
            "-- Overloads for convenience\n"
            "procedure log_hdr_large (\n"
            "  constant msg : in string) is\n"
            "begin  -- procedure log_hdr\n"
            "  log(ID_LOG_HDR_LARGE, msg, C_SCOPE);\n"
            "end procedure log_hdr_large;\n\n"
        )

        return s

    @staticmethod
    def log_hdr_large(string):
        return 'log_hdr_large("{}");\n'.format(string)

    @staticmethod
    def log_hdr(string):
        return 'log_hdr("{}");\n'.format(string)

    @staticmethod
    def check_value(signal, value, msg):
        s = 'check_value({}, {}, error, "{}");\n'.format(signal, value, msg)
        return s

    @staticmethod
    def await_value(signal, value, msg):
        s = 'await_value({}, {}, 0 ns, 1 ns, error, "{}");\n'.format(signal, value, msg)
        return s

    @staticmethod
    def await_stable(signal, clk_cycles, msg):
        s = 'await_stable({0}, {1}*C_CLK_PERIOD, FROM_LAST_EVENT, {1}*C_CLK_PERIOD, FROM_LAST_EVENT, error, "{2}");\n'.format(
            signal, clk_cycles, msg
        )
        return s

    def sig_value(self, value, sig_type, width=0):
        if sig_type == "sl":
            s = "'{}'".format(int(value, 16))
        elif sig_type == "slv":
            s = '{}X"{:x}"'.format(width, int(value, 16))
        elif sig_type == "default":
            s = '{}X"{:X}"'.format(self.bus.addr_width, int(value, 16))
        else:
            print(sig_type)
            raise Exception("Invalid signal type")
        return s

    @staticmethod
    def to_zero(sig_type):
        if sig_type == "sl":
            return "'0'"
        elif sig_type == "slv":
            return "(others => '0')"
        else:
            raise Exception("Invalid signal type")
