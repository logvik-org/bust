from bust.utils import NL, indent_string


def lib_declaration():
    s = (
        f"library ieee;{NL}"
        f"use ieee.std_logic_1164.all;{NL}"
        f"use ieee.numeric_std.all;{NL}"
    )
    return s


def ieee_math():
    # fmt: off
    s = (f"{lib_declaration()}"
         f"use ieee.math_real.all;{NL}")  # fmt: on
    return s


def sync_process(
    clk_name,
    reset_name,
    process_name,
    reset_string,
    logic_string,
    active_low=True,
    variables=None,
):
    s = f"{process_name} : process({clk_name}){NL}"
    if variables is not None:
        for var in variables:
            s += indent_string(f"variable {var};{NL}")
    s += (
        f"begin{NL}"
        f'{indent_string(f"if rising_edge({clk_name}) then{NL}")}'
        f'{indent_string(f"if {reset_name} = ", 2)}'
    )

    if active_low:
        s += "'0'"
    else:
        s += "'1'"

    s += (
        f" then{NL}"
        f'{indent_string(f"{reset_string}{NL}", 3)}'
        f'{indent_string(f"else{NL}", 2)}'
        f"{indent_string(logic_string, 3)}"
        f'{indent_string(f"end if;{NL}", 2)}'
        f'{indent_string(f"end if;{NL}")}'
    )

    s += f"end process {process_name};{NL}"
    return s


def async_process(
    clk_name,
    reset_name,
    process_name,
    reset_string,
    logic_string,
    active_low=True,
    variables=None,
):
    s = f"{process_name} : process({clk_name}, {reset_name}){NL}"
    if variables is not None:
        for var in variables:
            s += indent_string(f"variable {var};{NL}")
    s += f"begin{NL}" f'{indent_string("if " + reset_name + " = ")}'

    if active_low:
        s += "'0'"
    else:
        s += "'1'"

    s += (
        f" then{NL}"
        f'{indent_string(f"{reset_string}{NL}", 2)}'
        f'{indent_string(f"elsif rising_edge({clk_name}) then{NL}")}'
        f'{indent_string(f"{logic_string}{NL}", 2)}'
        f'{indent_string(f"end if;{NL}")}'
        f'{f"end process {process_name};{NL}"}'
    )

    return s


def comb_process(process_name, logic_string):
    s = f"{process_name} : process(all){NL}"
    s += f"begin{NL}{NL}"

    s += indent_string(logic_string)

    s += f"end process {process_name};{NL}"

    return s


def comb_process_with_reset(
    reset_name, process_name, reset_string, logic_string, active_low=True
):
    s = (
        f"{process_name} : process(all){NL}"
        f"begin{NL}"
        f'{indent_string(f"if {reset_name} = ")}'
    )

    if active_low:
        s += "'0'"
    else:
        s += "'1'"

    s += (
        f" then{NL}"
        f'{indent_string(f"{reset_string}{NL}", 2)}'
        f'{indent_string(f"else{NL}")}'
        f'{indent_string(f"{logic_string}{NL}", 2)}'
        f'{indent_string(f"end if;{NL}")}'
        f'{f"end process {process_name};{NL}"}'
    )

    return s
