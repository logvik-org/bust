"""Utility functions for bust.

This package contains utility functions for file operations, JSON processing,
and string formatting:

- file_utils: File I/O and path handling utilities
- json_utils: JSON parsing utilities
- formatting: String formatting utilities
"""

from bust.utils.file_utils import write_string_to_file
from bust.utils.json_utils import json_parser, compare_JSON
from bust.utils.formatting import (
    indent_string,
    fix_last_indent_only_line,
    is_mixed,
    NL,
    spaces_in_tab,
)

from bust.interaction import (
    InteractionHandler,
    ConsoleInteractionHandler,
    AutomatedInteractionHandler,
)

__all__ = [
    # File utilities
    "write_string_to_file",
    # JSON utilities
    "json_parser",
    "compare_JSON",
    # Formatting utilities
    "indent_string",
    "fix_last_indent_only_line",
    "is_mixed",
    "NL",
    "spaces_in_tab",
    # Interaction handlers
    "InteractionHandler",
    "ConsoleInteractionHandler",
    "AutomatedInteractionHandler",
]
