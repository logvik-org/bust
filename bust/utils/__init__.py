"""Utility functions for bust.

This package contains utility functions for file operations, JSON processing,
and string formatting:

- file_utils: File I/O and path handling utilities
- json_utils: JSON parsing utilities
- formatting: String formatting utilities
"""

from bust.utils.file_utils import (
    write_string_to_file,
    update_module_top_level,
    analyze_top_level_file,
    restore_user_in_top_level,
)
from bust.utils.json_utils import json_parser, compare_JSON
from bust.utils.formatting import (
    indent_string,
    add_line_breaks,
    splitkeepsep,
    fix_last_indent_only_line,
    is_mixed,
    NL,
    spaces_in_tab,
)

# User interaction utilities
from bust.utils.file_utils import (
    cont,
    is_int,
    get_int,
    get_list_choice,
    clear_screen,
)

__all__ = [
    # File utilities
    "write_string_to_file",
    "update_module_top_level",
    "analyze_top_level_file",
    "restore_user_in_top_level",
    # JSON utilities
    "json_parser",
    "compare_JSON",
    # Formatting utilities
    "indent_string",
    "add_line_breaks",
    "splitkeepsep",
    "fix_last_indent_only_line",
    "is_mixed",
    "NL",
    "spaces_in_tab",
    # User interaction
    "cont",
    "is_int",
    "get_int",
    "get_list_choice",
    "clear_screen",
]
