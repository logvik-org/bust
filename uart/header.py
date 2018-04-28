from uart.utils import indent_string


class Header(object):
    """Documentation for Header

    """
    def __init__(self, module):
        self.module = module

    def return_c_header(self):
        s = ''

        s += "#ifndef " + self.module.name.upper() + "_H\n"
        s += "#define " + self.module.name.upper() + "_H\n"
        s += "\n"

        s += "#define " + self.module.name.upper() + "_BASEADDR " + str(hex(self.module.baseaddr))
        s += "\n\n"

        for reg in self.module.registers:
            s += "/* Register: " + reg.name + " */\n"
            s += "#define " + reg.name.upper() + "_OFFSET " + str(hex(reg.address)) + "\n"
            s += "#define " + reg.name.upper() + "_RESET " + reg.reset + "\n"
            s += "\n"

            if reg.sig_type == "fields":
                for field in reg.fields:
                    s += "/* Field: " + field.name + " */\n"
                    s += "#define " + reg.name.upper() + "_" + field.name.upper() + "_OFFSET "
                    s += str(field.pos_low) + "\n"
                    s += "#define " + reg.name.upper() + "_" + field.name.upper() + "_WIDTH "
                    s += str(field.length) + "\n"
                    s += "#define " + reg.name.upper() + "_" + field.name.upper() + "_RESET "
                    s += field.reset + "\n"
                    s += "\n"

        s += "#endif"
        return s

    def return_python_header(self):
        s = ''

        s += "class " + self.module.name.upper() + "_H:\n\n"

        s += indent_string(self.module.name.upper() + "_BASEADDR = " + str(hex(self.module.baseaddr)), 2)
        s += "\n\n"

        for reg in self.module.registers:
            s += indent_string('""" Register: ' + reg.name + ' """\n', 2)
            s += indent_string(reg.name.upper() + "_OFFSET = " + str(hex(reg.address)) + "\n", 2)
            s += indent_string(reg.name.upper() + "_RESET = " + reg.reset + "\n", 2)
            s += "\n"

            if reg.sig_type == "fields":
                for field in reg.fields:
                    s += indent_string('""" Field: ' + field.name + ' """\n', 2)
                    s += indent_string(reg.name.upper() + "_" + field.name.upper() + "_OFFSET = ", 2)
                    s += str(field.pos_low) + "\n"
                    s += indent_string(reg.name.upper() + "_" + field.name.upper() + "_WIDTH = ", 2)
                    s += str(field.length) + "\n"
                    s += indent_string(reg.name.upper() + "_" + field.name.upper() + "_RESET = ", 2)
                    s += field.reset + "\n"
                    s += "\n"

        return s
