"""File I/O utilities for bust.

This module provides functions for file operations including writing files,
reading and updating VHDL source files, and user interaction utilities.
"""

import os
import logging
from typing import Any, List, Optional

from bust.utils.formatting import splitkeepsep

logger = logging.getLogger(__name__)


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


def cont() -> None:
    """Pause execution and wait for user to press Enter."""
    try:
        input("Press enter to continue...")
    except SyntaxError:
        # Handle Python 2 compatibility where input() without parentheses raises SyntaxError
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
