"""
filters.py

Custom Jinja2 filters for use across `bust` templates.

Filters defined:
- to_binary: Format an integer as a binary string for VHDL literals.
- utf8tolatex: Convert UTF-8 text to LaTeX-safe encoding.

Copyright (c) 2025 Ola Groettvik
Licensed under the Apache License, Version 2.0. See the LICENSE file for details.
"""


def to_binary(value, width):
    """Format an integer as a width-bit binary string for VHDL literals."""
    return f"{value:0{width}b}"


def utf8tolatex(text):
    """Convert UTF-8 text to LaTeX-safe encoding."""
    # Imported lazily so VHDL/header rendering does not require pylatexenc.
    from pylatexenc.latexencode import utf8tolatex as _utf8tolatex

    return _utf8tolatex(text)
