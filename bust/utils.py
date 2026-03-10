"""Utility functions for bust.

This module is a backward compatibility shim. Import from bust.utils subpackages instead.
"""

# Re-export from new locations for backward compatibility
from bust.utils.formatting import (
    indent_string,
    fix_last_indent_only_line,
    splitkeepsep,
    add_line_breaks,
    is_mixed,
    NL,
    spaces_in_tab,
)
from bust.utils.json_utils import json_parser, compare_JSON
from bust.utils.file_utils import (
    write_string_to_file,
    update_module_top_level,
    analyze_top_level_file,
    restore_user_in_top_level,
    cont,
    is_int,
    get_int,
    get_list_choice,
    clear_screen,
)
from bust.interaction import (
    InteractionHandler,
    ConsoleInteractionHandler,
    AutomatedInteractionHandler,
)

__all__ = [
    # Formatting utilities
    "indent_string",
    "fix_last_indent_only_line",
    "splitkeepsep",
    "add_line_breaks",
    "is_mixed",
    "NL",
    "spaces_in_tab",
    # JSON utilities
    "json_parser",
    "compare_JSON",
    # File utilities
    "write_string_to_file",
    "update_module_top_level",
    "analyze_top_level_file",
    "restore_user_in_top_level",
    # User interaction
    "cont",
    "is_int",
    "get_int",
    "get_list_choice",
    "clear_screen",
    # Interaction handlers
    "InteractionHandler",
    "ConsoleInteractionHandler",
    "AutomatedInteractionHandler",
]
