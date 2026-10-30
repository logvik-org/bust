"""
filters.py

Custom Jinja2 filters for use across `bust` templates.

Filters defined:
- to_binary: Format an integer as a binary string for VHDL literals.
- align: Line up a token, such as ":" or "<=", in a column.
- wrap: Break a call that is too long after a comma.
- utf8tolatex: Convert UTF-8 text to LaTeX-safe encoding.
- utf8tohtml: Escape text for HTML, with `code` spans as <code>.
- markdown_cell: Escape text for one cell of a Markdown table.
- align_markdown_tables: Pad the cells of every Markdown table into columns.

Copyright (c) 2025 Ola Groettvik
Licensed under the Apache License, Version 2.0. See the LICENSE file for details.
"""

import html
import re


def to_binary(value, width):
    """Format an integer as a width-bit binary string for VHDL literals."""
    return f"{value:0{width}b}"


_CONDITION = re.compile(r"(if|elsif|while|when|return|assert|report)\b")
_CONTROL = re.compile(r"(if|elsif|else|end|case|when|for|while|loop)\b")


def align(text, *tokens, nested=False):
    """Line up each token in a column, as the alignment rules of vsg do.

    A token is matched with a space before it and a space or the end of the
    line after it, such as " : ". "<=|:=" matches either of the two, so both
    line up in one column. A group is a run of lines with the same indentation
    that contain the token. A blank line, a comment line, a control statement
    such as if or end if, or a line with less indentation ends it. With
    `nested`, as in a constant with nested aggregates, a group also takes in
    the lines between that are indented more or do not contain the token, and
    ends only at a blank line or a line with less indentation. The token goes
    one space after the longest text in front of it in the group.
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
            stripped = line.strip()
            if nested:
                ends = not stripped or indent < base
            else:
                # Other statements, such as a wait, and the continuation lines
                # of a statement do not end a group.
                ends = (
                    not stripped
                    or stripped.startswith("--")
                    or bool(_CONTROL.match(stripped))
                    or indent < base
                    or (found and indent != base)
                )
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


def wrap(text, width=120):
    """Break each line longer than `width` that holds a call, as vsg accepts.

    The arguments of the first call on the line go on as many lines as needed,
    each continuation line starting one column after its opening parenthesis.
    """
    out = []
    for line in text.split("\n"):
        if len(line) <= width or "(" not in line:
            out.append(line)
            continue
        opening = line.index("(")
        parts, depth, start, quoted = [], 0, opening + 1, False
        for i in range(opening, len(line)):
            char = line[i]
            if char == '"':
                quoted = not quoted
            elif quoted:
                continue
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == "," and depth == 1:
                parts.append(line[start : i + 1].strip())
                start = i + 1
        parts.append(line[start:].strip())
        lines = [line[: opening + 1] + parts[0]]
        for part in parts[1:]:
            if len(lines[-1]) + 1 + len(part) <= width:
                lines[-1] += " " + part
            else:
                lines.append(" " * (opening + 1) + part)
        out.extend(lines)
    return "\n".join(out)


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
    return _convert_code_spans(
        text, encoder.unicode_to_latex, lambda code: "\\texttt{" + code + "}"
    )


def utf8tohtml(text):
    """Escape text for HTML, with a `code` span as <code>, as utf8tolatex sets
    it in typewriter type."""
    return _convert_code_spans(text, html.escape, lambda code: f"<code>{code}</code>")


def _convert_code_spans(text, convert, mark_code):
    """Convert all of `text`, and mark each `code` span in it after converting."""
    parts = re.split(r"`([^`]*)`", str(text))
    return "".join(
        convert(part) if i % 2 == 0 else mark_code(convert(part))
        for i, part in enumerate(parts)
    )


_MARKDOWN_SPECIAL = re.compile(r"([\\*\[\]<>|])")


def markdown_cell(text):
    """Escape text for one line of Markdown, such as a table cell.

    A `code` span is kept, but a | in it is still escaped, since GitHub splits
    the cells of a table row before it reads code spans. Line breaks become
    spaces.
    """
    parts = re.split(r"(`[^`]*`)", str(text))
    escaped = "".join(
        part.replace("|", "\\|") if i % 2 else _MARKDOWN_SPECIAL.sub(r"\\\1", part)
        for i, part in enumerate(parts)
    )
    return " ".join(escaped.split())


_MARKDOWN_DELIMITER_CELL = re.compile(r":?-+:?")


def _markdown_row_cells(line):
    """The cells of a table row. A backslash escapes the character after it, so
    an escaped | stays in its cell."""
    cells, cell, chars = [], "", iter(line.strip()[1:])
    for char in chars:
        if char == "\\":
            cell += char + next(chars, "")
        elif char == "|":
            cells.append(cell.strip())
            cell = ""
        else:
            cell += char
    return cells


def _aligned_markdown_table(rows):
    delimiter = rows[1]
    widths = [
        max(3, *(len(row[column]) for row in rows if row is not delimiter))
        for column in range(len(delimiter))
    ]
    lines = []
    for row in rows:
        cells = []
        for cell, width, spec in zip(row, widths, delimiter):
            if row is delimiter:
                left = ":" if spec.startswith(":") else "-"
                right = ":" if spec.endswith(":") else "-"
                cells.append(left + "-" * (width - 2) + right)
            elif spec.endswith(":") and not spec.startswith(":"):
                cells.append(cell.rjust(width))
            else:
                cells.append(cell.ljust(width))
        lines.append("| " + " | ".join(cells) + " |")
    return lines


def align_markdown_tables(text: str) -> str:
    """Pad the cells of every Markdown table so its columns line up in the
    source. A table is a run of lines that start with | and whose second line
    is the delimiter row. Rendered Markdown looks the same."""
    lines = text.split("\n")
    aligned, start = [], 0
    while start < len(lines):
        end = start
        while end < len(lines) and lines[end].lstrip().startswith("|"):
            end += 1
        rows = [_markdown_row_cells(line) for line in lines[start:end]]
        is_table = (
            len(rows) >= 2
            and all(_MARKDOWN_DELIMITER_CELL.fullmatch(cell) for cell in rows[1])
            and all(len(row) == len(rows[1]) for row in rows)
        )
        if is_table:
            aligned.extend(_aligned_markdown_table(rows))
            start = end
        else:
            aligned.append(lines[start])
            start += 1
    return "\n".join(aligned)
