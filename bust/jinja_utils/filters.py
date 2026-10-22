"""
filters.py

Custom Jinja2 filters for use across `bust` templates.

Filters defined:
- to_binary: Format an integer as a binary string for VHDL literals.
- utf8tolatex: Convert UTF-8 text to LaTeX-safe encoding.

Copyright (c) 2025 Ola Groettvik
Licensed under the Apache License, Version 2.0. See the LICENSE file for details.
"""

import re


def to_binary(value, width):
    """Format an integer as a width-bit binary string for VHDL literals."""
    return f"{value:0{width}b}"


def utf8tolatex(text):
    """Convert UTF-8 text to LaTeX-safe encoding.

    A `code` span becomes \\texttt, and a character LaTeX has no form for, such
    as an emoji, is left out.
    """
    # Imported lazily so VHDL/header rendering does not require pylatexenc.
    from pylatexenc.latexencode import UnicodeToLatexEncoder

    encoder = UnicodeToLatexEncoder(
        non_ascii_only=False,
        replacement_latex_protection="braces-all",
        unknown_char_policy="ignore",
        unknown_char_warning=False,
    )
    parts = re.split(r"`([^`]*)`", str(text))
    return "".join(
        (
            encoder.unicode_to_latex(part)
            if i % 2 == 0
            else "\\texttt{" + encoder.unicode_to_latex(part) + "}"
        )
        for i, part in enumerate(parts)
    )
