"""VHDL identifier validation utilities for bust.

This module provides functions for validating VHDL identifiers according to
the VHDL language standard (IEEE 1076). It checks for reserved keywords,
naming conventions, and uniqueness within a namespace.
"""

import logging
import re

from bust.utils.formatting import is_mixed

logger = logging.getLogger(__name__)


def is_VHDL_keyword(string):
    """Check if string is a VHDL reserved keyword.

    Args:
        string: String to check.

    Returns:
        True if string is a VHDL keyword, False otherwise.
    """
    keywords = [
        "abs",
        "access",
        "after",
        "alias",
        "all",
        "and",
        "architecture",
        "array",
        "assert",
        "assume",
        "assume_guarantee",
        "attribute",
        "begin",
        "block",
        "body",
        "buffer",
        "bus",
        "case",
        "component",
        "configuration",
        "constant",
        "context",
        "cover",
        "default",
        "disconnect",
        "downto",
        "else",
        "elsif",
        "end",
        "entity",
        "exit",
        "fairness",
        "file",
        "for",
        "force",
        "function",
        "generate",
        "generic",
        "group",
        "guarded",
        "if",
        "impure",
        "in",
        "inertial",
        "inout",
        "is",
        "label",
        "library",
        "linkage",
        "literal",
        "loop",
        "map",
        "mod",
        "nand",
        "new",
        "next",
        "nor",
        "not",
        "null",
        "of",
        "on",
        "open",
        "or",
        "others",
        "out",
        "package",
        "parameter",
        "port",
        "postponed",
        "procedure",
        "process",
        "property",
        "protected",
        "pure",
        "range",
        "record",
        "register",
        "reject",
        "release",
        "rem",
        "report",
        "restrict",
        "restrict_guarantee",
        "return",
        "rol",
        "ror",
        "select",
        "sequence",
        "severity",
        "shared",
        "signal",
        "sla",
        "sll",
        "sra",
        "srl",
        "strong",
        "subtype",
        "then",
        "to",
        "transport",
        "type",
        "unaffected",
        "units",
        "until",
        "use",
        "variable",
        "vmode",
        "vprop",
        "vunit",
        "wait",
        "when",
        "while",
        "with",
        "xnor",
        "xor",
    ]

    # VHDL is case-insensitive, so "ON" is the keyword "on".
    return string.lower() in keywords


def contain_spaces(string):
    """Check if string contains spaces.

    Args:
        string: String to check.

    Returns:
        True if string contains spaces.
    """
    return " " in string


def start_with_alphabetic_letter(string):
    """Check if string starts with a letter.

    Args:
        string: String to check.

    Returns:
        True if first character is alphabetic.
    """
    return string[0].isalpha()


def ends_with_underscore(string):
    """Check if string ends with underscore.

    Args:
        string: String to check.

    Returns:
        True if string ends with '_'.
    """
    return string.endswith("_")


def contain_two_successive_underscores(string):
    """Check if string contains two consecutive underscores.

    Args:
        string: String to check.

    Returns:
        True if string contains '__'.
    """
    return "__" in string


def is_only_alpfanum_(string):
    """Check if string contains only alphanumeric characters and underscores.

    Args:
        string: String to check.

    Returns:
        True if string contains only letters, digits, and underscores.
    """
    regex = re.compile(r"\W")
    return regex.search(string) is None


def is_valid_VHDL(string):
    """Validate string as a VHDL identifier.

    Checks all VHDL identifier rules from IEEE 1076:
    - Must not be empty
    - Must not be a reserved keyword
    - Must not contain spaces
    - Must start with a letter
    - Must not end with underscore
    - Must not contain consecutive underscores
    - Must contain only letters, digits, and underscores
    - Warns if longer than 16 characters
    - Warns if mixing uppercase and lowercase

    Args:
        string: String to validate.

    Returns:
        True if valid (warnings are printed but don't prevent validation).

    Raises:
        InvalidVHDLIdentifier: If string violates VHDL naming rules.
    """
    if len(string) < 1:
        raise InvalidVHDLIdentifier(string + " - identifier cannot be empty.")
    if is_VHDL_keyword(string):
        raise InvalidVHDLIdentifier(
            string + " - identifier cannot be identical to VHDL keyword."
        )
    if contain_spaces(string):
        raise InvalidVHDLIdentifier(string + " - identifiers cannot contain spaces.")
    if not start_with_alphabetic_letter(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers must start with an alphabetic letter."
        )
    if ends_with_underscore(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers cannot end with underscore."
        )
    if contain_two_successive_underscores(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers cannot contain two successive underscores."
        )
    if not is_only_alpfanum_(string):
        raise InvalidVHDLIdentifier(
            string + " - identifiers may only contain letters, digits and underscores."
        )
    if len(string) > 16:
        logger.warning(
            string + " - identifier should probably not be longer than 16 characters."
        )
    if is_mixed(string):
        logger.warning(
            string + " - identifier should probably not contain a mix of uppercase"
            " and lowercase letters."
        )
    return True


def is_unique(string, ls):
    """Check if identifier is unique within a namespace.

    Args:
        string: Identifier to check.
        ls: List of existing identifiers in the namespace.

    Returns:
        True if identifier is unique.

    Raises:
        NonUniqueIdentifer: If identifier already exists in the list.
    """
    # VHDL is case-insensitive, so "a" and "A" name the same thing.
    if string.lower() in (name.lower() for name in ls):
        raise NonUniqueIdentifer(
            string + " - identifier is already used in the same namespace."
        )
    return True


class InvalidVHDLIdentifier(Exception):
    """Raised when a string violates VHDL identifier naming rules.

    This exception is raised during validation when an identifier doesn't
    meet VHDL language requirements for naming.
    """

    def __init__(self, msg):
        """Initialize InvalidVHDLIdentifier exception.

        Args:
            msg: Description of the validation error.
        """
        super().__init__(f"Invalid identifier: {msg}")


class NonUniqueIdentifer(Exception):
    """Raised when an identifier is not unique within its namespace.

    This exception indicates an attempt to use an identifier that already
    exists in the same scope (e.g., duplicate register or field names).
    """

    def __init__(self, msg):
        """Initialize NonUniqueIdentifer exception.

        Args:
            msg: Description of the uniqueness violation.
        """
        super().__init__(f"Invalid identifier: {msg}")
