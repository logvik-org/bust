from bust.utils import indent_string


class Header(object):
    """Documentation for Header"""

    def __init__(self, module):
        self.module = module

    def return_c_header(self):
        s = ""

        s += "#ifndef " + self.module.name.upper() + "_H\n"
        s += "#define " + self.module.name.upper() + "_H\n"

        s += "\n\n"

        for reg in self.module.registers:
            s += "/* Register: " + reg.name + " */\n"
            s += (
                "#define "
                + reg.name.upper()
                + "_OFFSET "
                + str(hex(reg.address))
                + "\n"
            )
            s += "#define " + reg.name.upper() + "_RESET " + reg.reset + "\n"
            s += "\n"

            if reg.sig_type == "fields":
                for field in reg.fields:
                    s += "/* Field: " + field.name + " */\n"
                    s += (
                        "#define "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_OFFSET "
                    )
                    s += str(field.pos_low) + "\n"
                    s += (
                        "#define "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_WIDTH "
                    )
                    s += str(field.length) + "\n"
                    s += (
                        "#define "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_RESET "
                    )
                    s += field.reset + "\n"
                    s += (
                        "#define "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_MASK "
                    )
                    s += str(hex(pow(2, field.length) - 1 << field.pos_low)) + "\n"
                    s += "\n"

        s += "#endif"
        s += "\n"

        return s

    def return_cpp_header(self):
        s = ""

        s += "#ifndef " + self.module.name.upper() + "_H\n"
        s += "#define " + self.module.name.upper() + "_H\n"
        s += "\n"

        s += "#include <cstdint>\n\n"

        s += "namespace " + self.module.name.upper() + "\n"
        s += "{\n"

        for reg in self.module.registers:
            s += "/* Register: " + reg.name + " */\n"
            s += (
                "static const uint32_t "
                + reg.name.upper()
                + "_OFFSET = "
                + str(hex(reg.address))
                + ";\n"
            )
            s += (
                "static const uint32_t "
                + reg.name.upper()
                + "_RESET = "
                + reg.reset
                + ";\n"
            )
            s += "\n"

            if reg.sig_type == "fields":
                for field in reg.fields:
                    s += "/* Field: " + field.name + " */\n"
                    s += (
                        "static const uint32_t "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_OFFSET = "
                    )
                    s += str(field.pos_low) + ";\n"
                    s += (
                        "static const uint32_t "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_WIDTH = "
                    )
                    s += str(field.length) + ";\n"
                    s += (
                        "static const uint32_t "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_RESET = "
                    )
                    s += field.reset + ";\n"
                    s += (
                        "static const uint32_t "
                        + reg.name.upper()
                        + "_"
                        + field.name.upper()
                        + "_MASK = "
                    )
                    s += str(hex(pow(2, field.length) - 1 << field.pos_low)) + ";\n"
                    s += "\n"
        s += "};\n\n"

        s += "#endif"
        s += "\n"

        return s

    def return_python_header(self):
        s = ""

        s += "class " + self.module.name.upper() + "_H:\n"

        for reg in self.module.registers:
            s += "\n"
            s += indent_string('"""Register: ' + reg.name + '"""\n', 2)
            s += indent_string(
                reg.name.upper() + "_OFFSET = " + str(hex(reg.address)) + "\n", 2
            )
            s += indent_string(reg.name.upper() + "_RESET = " + reg.reset + "\n", 2)

            if reg.sig_type == "fields":
                for field in reg.fields:
                    s += "\n"
                    s += indent_string('""" Field: ' + field.name + ' """\n', 2)
                    s += indent_string(
                        reg.name.upper() + "_" + field.name.upper() + "_OFFSET = ", 2
                    )
                    s += str(field.pos_low) + "\n"
                    s += indent_string(
                        reg.name.upper() + "_" + field.name.upper() + "_WIDTH = ", 2
                    )
                    s += str(field.length) + "\n"
                    s += indent_string(
                        reg.name.upper() + "_" + field.name.upper() + "_RESET = ", 2
                    )
                    s += field.reset + "\n"
                    s += indent_string(
                        reg.name.upper() + "_" + field.name.upper() + "_MASK = ", 2
                    )
                    s += str(hex(pow(2, field.length) - 1 << field.pos_low))
                    s += "\n"

        return s

    def return_ipbus_addr_table(self):
        s = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        s += '<node id="{}">\n'.format(self.module.name)

        for reg in self.module.registers:
            par = '<node id="{}" address="0x{:08X}" permission="{}" description="{}" parameters="reset={}'.format(
                reg.name, reg.address, reg.get_mode(), reg.description, reg.reset
            )

            if reg.mode == "pulse":
                par += ";pulse_cycles={}".format(reg.pulse_cycles)
            if reg.stall:
                par += ";stall_cycles={}".format(reg.stall_cycles)
            if reg.sig_type == "fields":
                par += '">\n'
            else:
                par += '"/>\n'

            if reg.sig_type == "fields":
                for field in reg.fields:
                    par2 = '<node id="{}" mask="{}" description="{}" parameters="reset={}"/>\n'.format(
                        field.name,
                        hex(field.get_mask()),
                        field.description,
                        field.reset,
                    )
                    par += indent_string(par2, 2)

                par += "</node>\n"

            s += indent_string(par, 2)

        s += "</node>"
        s += "\n"

        return s
