from uart.utils import indent_string


def sync_process(clk_name, reset_name, process_name, reset_string, logic_string, active_low=True):
    s = process_name + " : process(" + clk_name + ")\n"
    s += "begin\n"
    s += indent_string("if rising_edge(" + clk_name + ") then\n")
    s += indent_string("if " + reset_name + " = ", 2)

    if active_low:
        s += "'0'"
    else:
        s += "'1'"

    s += " then\n"

    s += indent_string(reset_string, 3)
    s += "\n"
    s += indent_string("else\n", 2)

    s += indent_string(logic_string, 3)
    s += "\n"
    s += indent_string("end if;\n", 2)
    s += indent_string("end if;\n")
    s += "end process " + process_name + ";\n"
    return s


def async_process(clk_name, reset_name, process_name, reset_string, logic_string, active_low=True):
    s = process_name + " : process(" + clk_name + ", " + reset_name  +")\n"
    s += "begin\n"
    s += indent_string("if " + reset_name + " = ")

    if active_low:
        s += "'0'"
    else:
        s += "'1'"

    s += " then\n"

    s += indent_string(reset_string, 2)
    s += "\n"
    s += indent_string("elsif rising_edge(" + clk_name + ") then\n")

    s += indent_string(logic_string, 2)
    s += "\n"
    s += indent_string("end if;\n")
    s += "end process " + process_name + ";\n"
    
    return s

def comb_process(process_name, logic_string):
    s = process_name + " : process(all)\n"
    s += "begin\n\n"

    s += indent_string(logic_string)

    s += "end process " + process_name + ";\n"

    return s
