"""
filters.py

Custom Jinja2 filters for use across `bust` templates.

This module defines reusable Jinja filters such as `indent_all`, which applies
indentation to all non-empty lines of a multi-line string. These filters are
intended to improve formatting control in generated VHDL and related code
templates.

Filters defined:
- indent_all: Indent all non-empty lines by a given number of spaces.
- hex_format: Format a value as hexadecimal with specified width.
- utf8tolatex: Convert UTF-8 text to LaTeX-safe encoding.
- get_vhdl_type: Returns the correct VHDL type based on register properties.
- get_reset_value: Returns the formatted VHDL reset value for registers.

Copyright (c) 2025 Grottviq
All rights reserved.
"""

from pylatexenc.latexencode import utf8tolatex as _utf8tolatex


def indent_all(text, spaces=4):
    """Indent all non-empty lines in a multi-line string by the given number of spaces."""
    prefix = " " * spaces
    return "\n".join(
        f"{prefix}{line}" if line.strip() else line for line in text.splitlines()
    )


def hex_format(value, width):
    """Format a value as hexadecimal with specified width."""
    return f"{value:0{width}X}"


def utf8tolatex(text):
    """Convert UTF-8 text to LaTeX-safe encoding."""
    return _utf8tolatex(text)


def get_vhdl_type(reg, module_name):
    """Returns the correct VHDL type based on the register's type."""
    from bust.enums import RegisterType, FieldType

    if reg.type == RegisterType.DEFAULT or (
        reg.type in [RegisterType.VECTOR, FieldType.VECTOR] and reg.width == 32
    ):
        return f"t_{module_name}_data"
    elif reg.type in [RegisterType.VECTOR, FieldType.VECTOR]:
        return f"std_logic_vector({reg.width - 1} downto 0)"
    elif reg.type in [RegisterType.BIT, FieldType.BIT]:
        return "std_logic"
    elif reg.type == RegisterType.FIELDS:
        return f"t_{module_name}_{reg.mode.value}_{reg.name}"
    else:
        raise RuntimeError(f"Unknown signal type: {reg.type}")


def get_reset_value(reg):
    """Returns the formatted VHDL reset value."""
    from bust.enums import RegisterType

    if reg.type in [RegisterType.DEFAULT, RegisterType.VECTOR]:
        return (
            "(others => '0')"
            if reg.reset == "0x0"
            else f'{reg.width}X"{int(reg.reset, 16):X}"'
        )
    elif reg.type == RegisterType.FIELDS:
        return f"({', '.join([f'{field.name} => {field.get_reset_vhdl()}' for field in reg.fields])})"
    elif reg.type == RegisterType.BIT:
        return f"'{int(reg.reset, 16):X}'"
    else:
        raise RuntimeError(f"Unknown reset type: {reg.type}")
