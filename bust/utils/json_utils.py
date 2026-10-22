"""JSON utilities for bust.

This module provides functions for parsing and comparing JSON data,
particularly for module configuration files.
"""

import json
import re
from typing import Any

import json5

from bust.exceptions import FormatError

# How json5 places an error, as in '<string>:3 Unexpected "}" at column 5'.
_JSON5_ERROR = re.compile(r"<string>:(\d+) (.*) at column (\d+)", re.DOTALL)


def json_parser(filename: str = "module.json") -> Any:
    """Parse a JSON or JSON5 file and return its contents.

    JSON5 adds comments, trailing commas and hexadecimal numbers such as 0x1c.

    Args:
        filename: Path to JSON file (default: "module.json").

    Returns:
        Parsed JSON data as Python object.

    Raises:
        FormatError: If the file is neither JSON nor JSON5, with the line and
            column of the first error.
        OSError: If the file cannot be read.
    """
    with open(filename, encoding="utf-8") as fp:
        text = fp.read()
    return parse_json_text(text, filename)


def parse_json_text(text: str, filename: str) -> Any:
    """Parse the text of a JSON or JSON5 file.

    Raises:
        FormatError: As `json_parser`.
    """
    if not text.strip():
        raise FormatError(f"{filename} is empty")
    try:
        return json.loads(text)
    except json.JSONDecodeError as json_error:
        try:
            return json5.loads(text)
        except ValueError as json5_error:
            raise _syntax_error(filename, text, json_error, json5_error) from None


def _syntax_error(
    filename: str,
    text: str,
    json_error: json.JSONDecodeError,
    json5_error: ValueError,
) -> FormatError:
    """The error with its line and column.

    json words errors better and places them well in a JSON file. Where json
    stops at JSON5, such as a comment, the error is json5's.
    """
    place = (json_error.lineno, json_error.colno)
    problem = json_error.msg
    match = _JSON5_ERROR.fullmatch(str(json5_error))
    if _is_json5_at(text, json_error.pos) or problem.endswith(" at"):
        if match is None:
            return FormatError(f"{filename}: not valid JSON or JSON5: {json5_error}")
        json5_place = (int(match.group(1)), int(match.group(3)))
        if json5_place != place or problem.endswith(" at"):
            # json5 quotes the character it found, as in Unexpected """.
            problem = match.group(2).replace(
                'Unexpected "\n"', "Unexpected end of line"
            )
            problem = re.sub(r'^Unexpected "(.)"$', r"Unexpected '\1'", problem)
        place = json5_place
    return FormatError(f"{filename}:{place[0]}:{place[1]}: {problem}")


def _is_json5_at(text: str, pos: int) -> bool:
    """True if JSON5 allows what json stopped at: a comment, a single quote, a
    key without quotes, a hexadecimal number or a trailing comma."""
    char = text[pos : pos + 1]
    if char in ("/", "'", "+", ".") or char.isalnum() or char in "_$":
        return bool(char)
    if char in ("}", "]"):
        return text[:pos].rstrip().endswith(",")
    return False


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
