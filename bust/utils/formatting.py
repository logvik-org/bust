"""String formatting utilities for bust.

This module provides functions for string manipulation and formatting,
including indentation, line breaking, and text processing.
"""

import re

spaces_in_tab = 2
NL = "\n"


def indent_string(string: str, tabs: int = 1, break_line: bool = False) -> str:
    """Add indentation to all lines in a string.

    Args:
        string: Input string to indent.
        tabs: Number of tab levels to indent (default: 1).
        break_line: Whether to add trailing newline (default: False).

    Returns:
        Indented string with spaces added to each line.
    """

    indent = spaces_in_tab * tabs * (" ")
    # Add indent to every line and recreate string
    string_list = [indent + line for line in re.split(r"\n", string)]

    # Remove indent in empty lines
    for i, s in enumerate(string_list):
        if s == indent:
            string_list[i] = ""
    string = "\n".join(string_list)

    # Remove last string if it only contains indent
    string = fix_last_indent_only_line(string, tabs)

    if break_line:
        string += "\n"
    return string


def fix_last_indent_only_line(string: str, tabs: int) -> str:
    """Remove indentation from last line if it only contains spaces.

    Args:
        string: Input string to process.
        tabs: Number of tab levels used for indentation.

    Returns:
        String with empty last line if it previously only had indentation.
    """
    string_list = re.split(r"\n", string)
    if string_list[-1] == (spaces_in_tab * tabs * (" ")):
        string_list[-1] = ""

    string = "\n".join(string_list)
    return string


def add_line_breaks(string: str, min_length: int) -> str:
    """Add line breaks to long strings at word boundaries.

    Inserts newlines after spaces once a line exceeds the minimum length.

    Args:
        string: Input string to process.
        min_length: Minimum line length before inserting break.

    Returns:
        String with line breaks added at appropriate positions.
    """
    requirement = min_length
    replace = False
    positions = []
    for i, char in enumerate(string):
        if i > requirement:
            replace = True
        if replace and char == " ":
            positions.append(i)
            requirement = i + min_length
            replace = False
    for rep in positions:
        string = string[:rep] + "\n" + string[rep + 1 :]

    return string


def is_mixed(string: str) -> bool:
    """Check if string contains both uppercase and lowercase letters.

    Args:
        string: String to check.

    Returns:
        True if string has both upper and lowercase letters, False otherwise.
    """
    upper = False
    lower = False
    for letter in string:
        if letter.isupper():
            upper = True
        elif letter.islower():
            lower = True

    return upper and lower
