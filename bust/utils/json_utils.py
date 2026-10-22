"""JSON utilities for bust.

This module provides functions for parsing and comparing JSON data,
particularly for module configuration files.
"""

import json
from typing import Any

import json5


def json_parser(filename: str = "module.json") -> Any:
    """Parse a JSON or JSON5 file and return its contents.

    JSON5 adds comments, trailing commas and hexadecimal numbers such as 0x1c.

    Args:
        filename: Path to JSON file (default: "module.json").

    Returns:
        Parsed JSON data as Python object.
    """
    with open(filename, encoding="utf-8") as fp:
        text = fp.read()
    try:
        return json.loads(text)
    except ValueError:
        return json5.loads(text)


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
