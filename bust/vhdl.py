import re

from bust.utils import indent_string, is_mixed, NL


def lib_declaration():
    s = (
        f"library ieee;{NL}"
        f"use ieee.std_logic_1164.all;{NL}"
        f"use ieee.numeric_std.all;{NL}"
    )
    return s


def ieee_math():
    s = f"{lib_declaration()}"
    s += f"use ieee.math_real.all;{NL}"
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


def get_identifier(msg, ls=None):
    while True:
        try:
            identifier = input(msg)
            is_valid_VHDL(identifier)
            if ls is not None:
                is_unique(identifier, ls)
            return identifier
        except Exception as e:
            print(e)


def is_VHDL_keyword(string):
    keywords = [
        "abs",
        "access",
        "after",
        "alias",
        "all",
        "and",
        "architecture",
        "array",
        "assert",
        "assume",
        "assume_guarantee",
        "attribute",
        "begin",
        "block",
        "body",
        "buffer",
        "bus",
        "case",
        "component",
        "configuration",
        "constant",
        "context",
        "cover",
        "default",
        "disconnect",
        "downto",
        "else",
        "elsif",
        "end",
        "entity",
        "exit",
        "fairness",
        "file",
        "for",
        "force",
        "function",
        "generate",
        "generic",
        "group",
        "guarded",
        "if",
        "impure",
        "in",
        "inertial",
        "inout",
        "is",
        "label",
        "library",
        "linkage",
        "literal",
        "loop",
        "map",
        "mod",
        "nand",
        "new",
        "next",
        "nor",
        "not",
        "null",
        "of",
        "on",
        "open",
        "or",
        "others",
        "out",
        "package",
        "parameter",
        "port",
        "postponed",
        "procedure",
        "process",
        "property",
        "protected",
        "pure",
        "range",
        "record",
        "register",
        "reject",
        "release",
        "rem",
        "report",
        "restrict",
        "restrict_guarantee",
        "return",
        "rol",
        "ror",
        "select",
        "sequence",
        "severity",
        "shared",
        "signal",
        "sla",
        "sll",
        "sra",
        "srl",
        "strong",
        "subtype",
        "then",
        "to",
        "transport",
        "type",
        "unaffected",
        "units",
        "until",
        "use",
        "variable",
        "vmode",
        "vprop",
        "vunit",
        "wait",
        "when",
        "while",
        "with",
        "xnor",
        "xor",
    ]

    return string in keywords


def contain_spaces(string):
    return " " in string


def start_with_alphabetic_letter(string):
    return string[0].isalpha()


def ends_with_underscore(string):
    return string.endswith("_")


def contain_two_successive_underscores(string):
    return "__" in string


def is_only_alpfanum_(string):
    regex = re.compile(r"\W")
    return regex.search(string) is None


def is_valid_VHDL(string):
    if len(string) < 1:
        raise InvalidVHDLIdentifier(string + " - identifier cannot be empty.")
    if is_VHDL_keyword(string):
        raise InvalidVHDLIdentifier(
            string + " - identifier cannot be identical to VHDL keyword."
        )
    if contain_spaces(string):
        raise InvalidVHDLIdentifier(string + " - identifiers cannot contain spaces.")
    if not start_with_alphabetic_letter(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers must start with an alphabetic letter."
        )
    if ends_with_underscore(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers cannot end with underscore."
        )
    if contain_two_successive_underscores(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers cannot contain two successive underscores."
        )
    if not is_only_alpfanum_(string):
        raise InvalidVHDLIdentifier(
            string
            + f" - identifiers may only contain {NL}{NL}- alphabetic letters "
            + f"(‘A’ to ‘Z’ and ‘a’ to ‘z’), {NL}- decimal digits (‘0’ to ‘9’) "
            + f"{NL}- the underline character (‘_’)"
        )
    if len(string) > 16:
        print(
            f"{NL}Warning - "
            + string
            + " - identifier should probably not be longer than 16 characters."
        )
    if is_mixed(string):
        print(
            f"{NL}Warning - "
            + string
            + " - identifier should probably not contain a mix of uppercase"
            + " and lowercase letters."
        )
    return True


def is_unique(string, ls):
    if string in ls:
        raise NonUniqueIdentifer(
            string + " - identifier is already used in the same namespace."
        )
    return True


class InvalidVHDLIdentifier(Exception):
    def __init__(self, msg):
        s = f"{NL}Error in parsing identifier: {msg}"
        super().__init__(s)


class NonUniqueIdentifer(Exception):
    def __init__(self, msg):
        s = f"{NL}Error in parsing identifier: {msg}"
        super().__init__(s)
