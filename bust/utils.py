"""Utility functions for bust.

This module provides various utility functions for string manipulation,
file I/O, JSON processing, and user interaction. These utilities are used
throughout the bust tool for formatting output, managing files, and
parsing configurations.
"""

import re
import json
import os
from functools import reduce
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

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


def json_parser(filename: str = "module.json") -> Any:
    """Parse JSON file and return contents.

    Args:
        filename: Path to JSON file (default: "module.json").

    Returns:
        Parsed JSON data as Python object.
    """
    with open(filename) as json_data:
        d = json.load(json_data)
        return d


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


def compare_JSON(json1: str, json2: str, raise_error: bool = False) -> bool:
    """Compare two JSON strings line by line.

    Args:
        json1: First JSON string.
        json2: Second JSON string.
        raise_error: If True, raise exception on first difference (default: False).

    Returns:
        True if JSON strings are identical, False otherwise.

    Raises:
        Exception: If raise_error is True and strings differ.
    """
    for linenumber, (line1, line2) in enumerate(
        zip(json1.splitlines(), json2.splitlines())
    ):
        if line1 != line2:
            if raise_error:
                raise Exception("JSON differs at line: " + str(linenumber))
            return False

    return True


def write_string_to_file(
    string: str, output_file: str, output_dir: str, force_overwrite: bool = False
) -> bool:
    """Write string content to a file with optional overwrite confirmation.

    Args:
        string: Content to write to file.
        output_file: Filename to write.
        output_dir: Directory path where file will be written.
        force_overwrite: Skip confirmation if file exists (default: False).

    Returns:
        True if file was written, False if user declined overwrite.

    Raises:
        RuntimeError: If output directory doesn't exist.
    """

    # Make sure output directory exists
    if not os.path.isdir(output_dir):
        raise RuntimeError(f"Output dir does not exist: {output_dir}")

    joined = os.path.join(output_dir, output_file)

    # Check if file exist
    if os.path.isfile(joined):
        if (
            not force_overwrite
            and input("Do you want to overwrite " + joined + "? (y/N):").upper() != "Y"
        ):
            logger.warning("Did not write " + joined)
            return False

    logger.debug("Writing string to " + joined)

    with open(joined, "w") as strfile:
        strfile.write(string)
    return True


def update_module_top_level(existing_file: str, new_top_level: str) -> str:
    """Update top-level VHDL module preserving user-edited sections.

    This function reads an existing top-level VHDL file, extracts user-edited
    sections (marked with special comments), and merges them into a newly
    generated top-level file.

    Args:
        existing_file: Path to existing top-level VHDL file.
        new_top_level: Newly generated top-level VHDL content.

    Returns:
        Updated VHDL content with user sections preserved.

    Raises:
        Exception: If user cancels the update operation.
    """
    # Check if file exists at all...
    if os.path.isfile(existing_file):
        # Read the file and get the user edited parts...
        string_list = analyze_top_level_file(existing_file)
        string = restore_user_in_top_level(string_list, new_top_level)
        if (
            input("Preview updated top-level before writing to file? (y/N): ").upper()
            == "Y"
        ):
            print(string)

        if (
            input("Are you sure want to update " + existing_file + "? (Y/n): ").upper()
            == "N"
        ):
            raise Exception("Cancelled update. Will keep existing top-level module.")
        else:
            return string
    else:
        logger.warning("Top-level file does not exist. Cannot update...")
        return new_top_level


def analyze_top_level_file(existing_file: str) -> List[str]:
    """Extract user-edited sections from existing top-level VHDL file.

    Args:
        existing_file: Path to existing VHDL file.

    Returns:
        List of 5 strings containing user sections: libraries, generics,
        ports, architecture, and logic.
    """
    string_list = [""] * 5
    list_num = 0
    with open(existing_file) as infile:
        copy = False
        for line in infile:
            if line.strip() == "-- User Libraries Start":
                copy = True
                list_num = 0
            elif line.strip() == "-- User Libraries End":
                copy = False
            elif line.strip() == "-- User Generics Start":
                copy = True
                list_num = 1
            elif line.strip() == "-- User Generics End":
                copy = False
            elif line.strip() == "-- User Ports Start":
                copy = True
                list_num = 2
            elif line.strip() == "-- User Ports End":
                copy = False
            elif line.strip() == "-- User Architecture Start":
                copy = True
                list_num = 3
            elif line.strip() == "-- User Architecture End":
                copy = False
            elif line.strip() == "-- User Logic Start":
                copy = True
                list_num = 4
            elif line.strip() == "-- User Logic End":
                copy = False
            elif copy:
                string_list[list_num] = string_list[list_num] + line

    return string_list


def restore_user_in_top_level(user: List[str], new_top_level: str) -> str:
    """Merge user-edited sections into new top-level VHDL content.

    Args:
        user: List of 5 user-edited sections from analyze_top_level_file().
        new_top_level: Newly generated top-level VHDL content.

    Returns:
        Merged VHDL content with user sections inserted at markers.
    """

    new_top_lines = splitkeepsep(new_top_level, "\n")

    top_lines_with_user = []
    last_was_marker = False
    for line in new_top_lines:
        if not last_was_marker:
            top_lines_with_user.append(line)
        last_was_marker = False
        if line.strip() == "-- User Libraries Start":
            top_lines_with_user += splitkeepsep(user[0], "\n")
            last_was_marker = True
        if line.strip() == "-- User Generics Start":
            top_lines_with_user += splitkeepsep(user[1], "\n")
            last_was_marker = True
        if line.strip() == "-- User Ports Start":
            top_lines_with_user += splitkeepsep(user[2], "\n")
            last_was_marker = True
        if line.strip() == "-- User Architecture Start":
            top_lines_with_user += splitkeepsep(user[3], "\n")
            last_was_marker = True
        if line.strip() == "-- User Logic Start":
            top_lines_with_user += splitkeepsep(user[4], "\n")
            last_was_marker = True

    return "".join(top_lines_with_user)


def splitkeepsep(s: str, sep: str) -> List[str]:
    """Split string while keeping separator with each segment.

    Args:
        s: String to split.
        sep: Separator string.

    Returns:
        List of strings where each element ends with the separator.
    """
    return reduce(
        lambda acc, elem: acc[:-1] + [acc[-1] + elem] if elem == sep else acc + [elem],
        re.split("(%s)" % re.escape(sep), s),
        [],
    )


def cont() -> None:
    """Pause execution and wait for user to press Enter."""
    try:
        input("Press enter to continue...")
    except SyntaxError:
        pass


def is_int(s: Any) -> bool:
    """Check if a value can be converted to an integer.

    Args:
        s: Value to check.

    Returns:
        True if s can be converted to int, False otherwise.
    """
    try:
        int(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata

        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False


def get_int(
    msg: str,
    base: int = 10,
    range_min: Optional[int] = None,
    range_max: Optional[int] = None,
    range_min_msg: Optional[str] = None,
    range_max_msg: Optional[str] = None,
    default: Optional[int] = None,
) -> int:
    """Prompt user for integer input with validation.

    Args:
        msg: Prompt message to display.
        base: Number base for parsing (default: 10).
        range_min: Minimum allowed value (optional).
        range_max: Maximum allowed value (optional).
        range_min_msg: Custom error message for minimum violation (optional).
        range_max_msg: Custom error message for maximum violation (optional).
        default: Default value if user presses Enter without input (optional).

    Returns:
        Valid integer within specified range.
    """
    while True:
        try:
            s = input(msg)
            if s == "" and default is not None:
                i = default
            else:
                i = int(s, base)
            if range_min is not None and i < range_min:
                if range_min_msg is None:
                    print("Integer must be at least " + str(range_min))
                else:
                    print(range_min_msg)
            elif range_max is not None and i > range_max:
                if range_max_msg is None:
                    print("Integer can't be larger than " + str(range_max))
                else:
                    print(range_max_msg)
            else:
                return i
        except Exception:
            print("That is not a valid integer...")


def get_list_choice(
    msg: str, ls: List[str], case: Optional[str] = None, default: Optional[int] = None
) -> str:
    """Prompt user to select from a list of options.

    Args:
        msg: Prompt message to display.
        ls: List of options to choose from.
        case: Optional case conversion ("lower", "upper", or None).
        default: Default option index (0-based) if user presses Enter (optional).

    Returns:
        Selected string from the list, optionally case-converted.
    """
    while True:
        try:
            print(msg)
            for i, element in enumerate(ls):
                if default is not None and i == default:
                    print(str(i + 1) + ": " + element.upper() + " - default")
                else:
                    print(str(i + 1) + ": " + element)
            tmp = input("Select by number: ")
            if default is not None and tmp == "":
                select = default + 1
            else:
                select = int(tmp)
            if select < 1 or select > len(ls):
                print(str(select) + " is not a valid choice...")
            else:
                if case == "lower":
                    return ls[select - 1].lower()
                elif case == "upper":
                    return ls[select - 1].upper()
                else:
                    return ls[select - 1]
        except Exception as e:
            print("That is not a valid choice...")


def clear_screen() -> None:
    """Clear the terminal screen (cross-platform)."""
    os.system("cls" if os.name == "nt" else "clear")


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
