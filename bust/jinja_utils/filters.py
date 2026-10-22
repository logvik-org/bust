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


_CONDITION = re.compile(r"(if|elsif|while|when|return|assert|report)\b")


def align(text, *tokens, nested=False):
    """Line up each token in a column, as the alignment rules of vsg do.

    A token is matched with a space before it and a space or the end of the
    line after it, such as " : ". "<=|:=" matches either of the two, so both
    line up in one column. A group is a run of consecutive lines with the same
    indentation that contain the token, and the continuation lines of their
    statements. With `nested`, as in a constant with nested aggregates, a
    group also takes in the lines between that are indented more or do not
    contain the token, and ends only at a blank line or a line with less
    indentation. The token goes one space after the longest text in front of
    it in the group.
    """
    lines = text.split("\n")
    for token in tokens:
        group: list = []
        base = 0
        for number, line in enumerate(lines + [""]):
            indent = len(line) - len(line.lstrip())
            position = min(
                (
                    p
                    for t in token.split("|")
                    for p in [
                        line.find(f" {t} "),
                        len(line) - len(t) - 1 if line.endswith(f" {t}") else -1,
                    ]
                    if p > indent
                ),
                default=-1,
            )
            # A comparison in a condition, such as if (a <= b), is no assignment.
            found = position > indent and not _CONDITION.match(line.strip())
            if nested:
                ends = not line.strip() or indent < base
            else:
                # A more deeply indented line without the token continues the
                # statement above it.
                ends = not line.strip() or indent < base or found != (indent == base)
            if group and ends:
                width = max(len(lines[n][:p].rstrip()) for n, p in group)
                for n, p in group:
                    head, tail = lines[n][:p].rstrip(), lines[n][p:].lstrip()
                    lines[n] = f"{head.ljust(width)} {tail}"
                group = []
            if found:
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
