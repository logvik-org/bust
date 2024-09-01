from symbol import if_stmt
from bust.utils import NL, indent_string
from bust.vhdl_gen_if import if_stmt, if_else_stmt, if_elseif_stmt


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


def clock_condition(clk_identifier):
    return f"rising_edge({clk_identifier})"


def reset_condition(reset_identifier, reset_active_high):
    return f"""{reset_identifier} = {"'1'" if reset_active_high else "'0'"}"""


def process(process_identifier, sensitivity_list, logic, variables=None):
    s = f"{process_identifier} : process({sensitivity_list}){NL}"
    if variables is not None:
        for var in variables:
            s += indent_string(f"variable {var};{NL}")
    s += f"begin{NL}"
    s += indent_string(logic)
    s += f"end process {process_identifier};{NL}"
    return s


def seq_process(
    process_identifier,
    clk_identifier,
    logic,
    reset_identifier=None,
    reset_logic=None,
    reset_active_high=None,
    reset_async=None,
    variables=None,
):
    if reset_identifier is not None:
        if reset_active_high is None or reset_async is None or reset_logic is None:
            raise ValueError("reset_active_high must be set")
        if reset_async:
            return _seq_process_async_reset(
                process_identifier,
                clk_identifier,
                logic,
                reset_identifier,
                reset_logic,
                reset_active_high,
                variables,
            )
        else:
            return _seq_process_sync_reset(
                process_identifier,
                clk_identifier,
                logic,
                reset_identifier,
                reset_logic,
                reset_active_high,
                variables,
            )
    else:
        raise NotImplementedError("Process without reset not implemented")


def _seq_process_sync_reset(
    process_identifier,
    clk_identifier,
    logic,
    reset_identifier,
    reset_logic,
    reset_active_high=True,
    variables=None,
):
    logic_block = if_else_stmt(
        reset_condition(reset_identifier, reset_active_high), reset_logic, logic
    )
    clocked_block = if_stmt(clock_condition(clk_identifier), logic_block)
    return process(
        process_identifier,
        _sensitivity_list_seq_process(clk_identifier, reset_identifier),
        clocked_block,
        variables,
    )


def _seq_process_async_reset(
    process_identifier,
    clk_identifier,
    logic,
    reset_identifier,
    reset_logic,
    reset_active_high=True,
    variables=None,
):

    reset_block = if_elseif_stmt(
        reset_condition(reset_identifier, reset_active_high),
        reset_logic,
        clock_condition(clk_identifier),
        logic,
    )
    return process(
        process_identifier,
        _sensitivity_list_seq_process(clk_identifier, reset_identifier),
        reset_block,
        variables,
    )


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


def _sensitivity_list_seq_process(clk_identifier, reset_identifier):
    return f"{clk_identifier}, {reset_identifier}"
