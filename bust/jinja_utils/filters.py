"""
filters.py

Custom Jinja2 filters for use across `bust` templates.

This module defines reusable Jinja filters such as `indent_all`, which applies
indentation to all non-empty lines of a multi-line string. These filters are
intended to improve formatting control in generated VHDL and related code
templates.

Filters defined:
- indent_all: Indent all non-empty lines by a given number of spaces.

Copyright (c) 2025 Grottviq
All rights reserved.
"""


def indent_all(text, spaces=4):
    """Indent all non-empty lines in a multi-line string by the given number of spaces."""
    prefix = " " * spaces
    return "\n".join(
        f"{prefix}{line}" if line.strip() else line for line in text.splitlines()
    )
