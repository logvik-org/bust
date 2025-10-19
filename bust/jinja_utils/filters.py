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
