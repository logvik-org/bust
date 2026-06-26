"""File I/O utilities for bust.

This module provides functions for file operations including writing files,
reading and updating VHDL source files, and user interaction utilities.
"""

import os
import logging
from typing import Any, List, Optional

from bust.interaction import InteractionHandler, ConsoleInteractionHandler

logger = logging.getLogger(__name__)


def write_string_to_file(
    string: str,
    output_file: str,
    output_dir: str,
    force_overwrite: bool = False,
    interaction_handler: Optional[InteractionHandler] = None,
) -> bool:
    """Write string content to a file with optional overwrite confirmation.

    Args:
        string: Content to write to file.
        output_file: Filename to write.
        output_dir: Directory path where file will be written.
        force_overwrite: Skip confirmation if file exists (default: False).
        interaction_handler: Handler used to ask the user whether to overwrite
            an existing file when *force_overwrite* is False.  Defaults to a
            :class:`~bust.interaction.ConsoleInteractionHandler` so that the
            function behaves identically to its original form when called
            without this argument.

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
        if not force_overwrite:
            handler: InteractionHandler = (
                interaction_handler
                if interaction_handler is not None
                else ConsoleInteractionHandler()
            )
            if handler(f"Do you want to overwrite {joined}? (y/N):").upper() != "Y":
                logger.warning(f"Did not write {joined}")
                return False

    logger.debug(f"Writing string to {joined}")

    with open(joined, "w") as strfile:
        strfile.write(string)
    return True


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
