from bust.utils import indent_string
from bust.vhdl import lib_declaration


class ModuleVHDLGen:
    def __init__(self, name, bus_gen, regs, data_width, addr_width):
        """Code generator for the Module module."""
        self.name = name
        self.bus = bus_gen
        self.registers = regs
        self.data_width = data_width
        self.addr_width = addr_width
        self.n_rw_regs = len([reg for reg in self.registers if reg.mode == "rw"])
        self.n_ro_regs = len([reg for reg in self.registers if reg.mode == "ro"])
        self.n_pulse_regs = len([reg for reg in self.registers if reg.mode == "pulse"])

    def return_module_pkg_VHDL(self):
        s = lib_declaration()
        s += "\n"
        s += "package " + self.name + "_pif_pkg is"
        s += "\n\n"

        s += self.get_subtypes_and_addrs_vhdl()

        if self.n_rw_regs > 0:
            s += self.get_rw_regs_vhdl()

        if self.n_ro_regs > 0:
            s += self.get_ro_regs_vhdl()

        if self.n_pulse_regs > 0:
            s += self.get_pulse_regs_vhdl()

        s += "\n"

        s += "end package " + self.name + "_pif_pkg;"
        s += "\n"

        return s

    def get_pulse_regs_vhdl(self):
        s = indent_string("-- PULSE Register Record Definitions\n\n")
        # Create all types for PULSE registers with records
        for reg in self.registers:
            if reg.mode == "pulse" and reg.sig_type == "fields":
                s += self.record_fields_definition_vhdl(reg)
        # The PULSE register record type
        s += indent_string("type t_" + self.name + "_pulse_regs is record\n")
        for reg in self.registers:
            if reg.mode == "pulse":
                s += indent_string(reg.name, 2) + " : "
                if reg.sig_type == "default" or (
                    reg.sig_type == "slv" and reg.length == self.data_width
                ):
                    s += "t_" + self.name + "_data;\n"
                elif reg.sig_type == "slv":
                    s += "std_logic_vector(" + str(reg.length - 1) + " downto 0);\n"
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
        gen = [reg for reg in self.registers if reg.mode == "pulse"]
        s += self.get_field_declarations(gen)
        s += "\n"
        return s

    def get_ro_regs_vhdl(self):
        s = indent_string("-- RO Register Record Definitions\n\n")
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
                if reg.sig_type == "default" or (
                    reg.sig_type == "slv" and reg.length == self.data_width
                ):
                    s += "t_" + self.name + "_data;\n"
                elif reg.sig_type == "slv":
                    s += "std_logic_vector(" + str(reg.length - 1) + " downto 0);\n"
                elif reg.sig_type == "sl":
                    s += "std_logic;\n"
                elif reg.sig_type == "fields":
                    s += "t_" + self.name + "_ro_" + reg.name + ";\n"
                else:
                    raise RuntimeError(
                        "Something went wrong... What now?" + reg.sig_type
                    )
        s += indent_string("end record;\n")
        s += "\n"
        s += indent_string("-- RO Register Reset Value Constant\n\n")
        s += indent_string("constant c_") + self.name + "_ro_regs : t_"
        s += self.name + "_ro_regs := (\n"
        gen = [reg for reg in self.registers if reg.mode == "ro"]
        s += self.get_field_declarations(gen)
        return s

    @staticmethod
    def get_field_reset_value(reg):
        par = ""
        if len(reg.fields) > 1:
            par += "(\n"
        else:
            par += "("
        for j, field in enumerate(reg.fields):
            if len(reg.fields) > 1:
                par += indent_string(field.name + " => ")
            else:
                par += field.name + " => "

            if field.sig_type == "slv":

                if field.reset == "0x0":
                    par += "(others => '0')"
                else:
                    par += str(field.length) + 'X"'
                    par += format(int(field.reset, 16), "X") + '"'

            elif field.sig_type == "sl":
                par += "'" + format(int(field.reset, 16), "X") + "'"

            if j < len(reg.fields) - 1:
                par += ",\n"
        par += ")"
        return par

    def get_rw_regs_vhdl(self):
        s = indent_string("-- RW Register Record Definitions\n\n")
        # Create all types for RW registers with records
        for reg in self.registers:
            if reg.mode == "rw" and reg.sig_type == "fields":
                s += self.record_fields_definition_vhdl(reg)
        # The RW register record type
        s += indent_string("type t_" + self.name + "_rw_regs is record\n")
        for reg in self.registers:
            if reg.mode == "rw":
                s += indent_string(reg.name, 2) + " : "
                if reg.sig_type == "default" or (
                    reg.sig_type == "slv" and reg.length == self.data_width
                ):
                    s += "t_" + self.name + "_data;\n"
                elif reg.sig_type == "slv":
                    s += "std_logic_vector(" + str(reg.length - 1) + " downto 0);\n"
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
        gen = [reg for reg in self.registers if reg.mode == "rw"]
        s += self.get_field_declarations(gen)
        s += "\n"
        return s

    def get_field_declarations(self, gen):
        s = ""
        for i, reg in enumerate(gen):
            par = ""
            par += reg.name + " => "

            # default values must be declared
            if reg.sig_type == "default" or reg.sig_type == "slv":
                if reg.reset == "0x0":
                    par += "(others => '0')"
                else:
                    par += str(reg.length) + 'X"'
                    par += format(int(reg.reset, 16), "X") + '"'

            elif reg.sig_type == "fields":
                par += self.get_field_reset_value(reg)

            elif reg.sig_type == "sl":
                par += "'" + format(int(reg.reset, 16), "X") + "'"
            else:
                raise RuntimeError("Something went wrong... What now?" + reg.sig_type)

            if i < len(gen) - 1:
                par += ","
            else:
                par += ");"
            par += "\n"

            s += indent_string(par, 2)
        return s

    def record_fields_definition_vhdl(self, reg):
        s = indent_string("type t_" + self.name + "_" + reg.mode + "_")
        s += reg.name + " is record\n"
        for field in reg.fields:
            s += indent_string(field.name, 2) + " : "
            if field.sig_type == "slv":
                s += "std_logic_vector(" + str(field.length - 1)
                s += " downto 0);\n"
            elif field.sig_type == "sl":
                s += "std_logic;\n"
            else:
                raise RuntimeError("Something went wrong..." + field.sig_type)
        s += indent_string("end record;\n\n")
        return s

    def get_subtypes_and_addrs_vhdl(self):
        par = ""
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
            par += 'X"' + "%X" % reg.address + '";\n'
        par += "\n"
        return indent_string(par)

    def return_module_VHDL(self):
        s = lib_declaration()
        s += "-- User Libraries Start\n\n"
        s += "-- User Libraries End\n"
        s += "\n"
        if self.bus.comp_library != "work":
            s += "library " + self.bus.comp_library + ";\n"
        if self.bus.bus_type == "ipbus":
            s += "use " + self.bus.comp_library + "." + self.bus.bus_type + ".all;\n"
        else:
            s += (
                "use " + self.bus.comp_library + "." + self.bus.bus_type + "_pkg.all;\n"
            )
        s += "use work." + self.name + "_pif_pkg.all;\n"
        s += "\n"

        s += "entity " + self.name + " is\n"
        s += "\n"
        s += indent_string("generic (\n")
        par = "-- User Generics Start\n\n"
        par += "-- User Generics End\n"
        par += "-- " + self.bus.bus_type.upper() + " Bus Interface Generics\n"
        par += (
            "g_"
            + self.bus.short_name
            + "_baseaddr        : std_logic_vector("
            + str(self.bus.addr_width - 1)
        )
        par += " downto 0) := (others => '0'));\n"

        s += indent_string(par, 2)

        s += indent_string("port (\n")
        par = "-- User Ports Start\n\n"
        par += "-- User Ports End\n"
        par += "-- {} Bus Interface Ports\n".format(self.bus.bus_type.upper())
        par += "{}_{}      : in  std_logic;\n".format(
            self.bus.short_name, self.bus.clk_name
        )
        par += "{}_{} : in  std_logic;\n".format(
            self.bus.short_name, self.bus.reset_name
        )
        par += "{}_in       : in  {};\n".format(self.bus.short_name, self.bus.in_type)
        par += "{}_out      : out {}\n".format(self.bus.short_name, self.bus.out_type)
        par += ");\n"
        s += indent_string(par, 2)
        s += "\n"
        s += "end entity " + self.name + ";\n"
        s += "\n"

        s += "architecture behavior of " + self.name + " is\n"
        s += "\n"
        par = "-- User Architecture Start\n\n"
        par += "-- User Architecture End\n\n"
        s += indent_string(par)

        s += indent_string(
            "-- " + self.bus.bus_type.upper() + " output signal for user readback\n"
        )
        par = "signal {}_out_i : {};\n".format(self.bus.short_name, self.bus.out_type)
        s += indent_string(par)

        s += indent_string("-- Register Signals\n")
        if self.n_rw_regs > 0:
            s += indent_string("signal " + self.bus.short_name + "_rw_regs    : t_")
            s += self.name + "_rw_regs    := c_" + self.name + "_rw_regs;\n"
        if self.n_ro_regs > 0:
            s += indent_string("signal " + self.bus.short_name + "_ro_regs    : t_")
            s += self.name + "_ro_regs    := c_" + self.name + "_ro_regs;\n"
        if self.n_pulse_regs > 0:
            s += indent_string("signal " + self.bus.short_name + "_pulse_regs : t_")
            s += self.name + "_pulse_regs := c_" + self.name + "_pulse_regs;\n"

        if self.n_rw_regs + self.n_ro_regs + self.n_pulse_regs > 0:
            s += "\n"

        s += "begin\n"
        s += "\n"

        par = "-- User Logic Start\n\n"
        par += "-- User Logic End\n\n"
        s += indent_string(par)

        s += indent_string(
            self.bus.short_name + "_out <= " + self.bus.short_name + "_out_i;\n\n"
        )

        s += indent_string(
            self.get_instantiation("i_{}_{}_pif".format(self.name, self.bus.short_name))
        )

        s += "\n"
        s += "end architecture behavior;"
        s += "\n"

        return s

    def get_instantiation(self, instance_name, intern_out=True):
        s = instance_name + " "
        s += ": entity work." + self.name + "_" + self.bus.short_name + "_pif\n"
        s += indent_string("generic map (\n")
        par = "g_{0}_baseaddr      => g_{0}_baseaddr)\n".format(self.bus.short_name)
        s += indent_string(par, 2)

        s += indent_string("port map (\n")
        if intern_out:
            inter = "_i"
        else:
            inter = ""

        par = ""
        if self.n_rw_regs > 0:
            par += (
                self.bus.short_name
                + "_rw_regs         => "
                + self.bus.short_name
                + "_rw_regs,\n"
            )
        if self.n_ro_regs > 0:
            par += (
                self.bus.short_name
                + "_ro_regs         => "
                + self.bus.short_name
                + "_ro_regs,\n"
            )
        if self.n_pulse_regs > 0:
            par += (
                self.bus.short_name
                + "_pulse_regs      => "
                + self.bus.short_name
                + "_pulse_regs,\n"
            )

        par += (
            self.bus.clk_name
            + "                 => "
            + self.bus.short_name
            + "_"
            + self.bus.clk_name
            + ",\n"
        )
        par += (
            self.bus.reset_name
            + "            => "
            + self.bus.short_name
            + "_"
            + str.strip(self.bus.reset_name)
            + ",\n"
        )
        par += self.bus.get_instantiation(self.name, inter)

        par += ");\n"

        s += indent_string(par, 2)
        return s
