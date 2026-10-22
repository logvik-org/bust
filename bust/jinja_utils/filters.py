"""
filters.py

Custom Jinja2 filters for use across `bust` templates.

Filters defined:
- to_binary: Format an integer as a binary string for VHDL literals.
- align: Line up a token, such as ":" or "<=", in a column.
- utf8tolatex: Convert UTF-8 text to LaTeX-safe encoding.

Copyright (c) 2025 Ola Groettvik
Licensed under the Apache License, Version 2.0. See the LICENSE file for details.
"""

import re


def to_binary(value, width):
    """Format an integer as a width-bit binary string for VHDL literals."""
    return f"{value:0{width}b}"


def align(text, *tokens):
    """Line up each token in a column, as the alignment rules of vsg do.

    A token is matched with a space before it and a space or the end of the
    line after it, such as " : ". A group of lines starts at the first line
    with the token and ends at a blank line or a line with less indentation.
    More deeply indented lines, such as a nested aggregate, belong to the
    group. The token goes one space after the longest text in front of it in
    the group.
    """
    lines = text.split("\n")
    for token in tokens:
        group: list = []
        base = 0
        for number, line in enumerate(lines + [""]):
            indent = len(line) - len(line.lstrip())
            if group and (not line.strip() or indent < base):
                width = max(len(lines[n][:p].rstrip()) for n, p in group)
                for n, p in group:
                    head, tail = lines[n][:p].rstrip(), lines[n][p:].lstrip()
                    lines[n] = f"{head.ljust(width)} {tail}"
                group = []
            position = line.find(f" {token} ")
            if position < 0 and line.endswith(f" {token}"):
                position = len(line) - len(token) - 1
            if position > indent:
                if not group:
                    base = indent
                group.append((number, position))
    return "\n".join(lines)


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
