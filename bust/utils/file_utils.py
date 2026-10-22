"""File I/O utilities for bust.

This module provides functions for file operations including writing files,
reading and updating VHDL source files.
"""

import os
import sys
import logging
from typing import Optional

from bust.interaction import InteractionHandler, ConsoleInteractionHandler

logger = logging.getLogger(__name__)


def may_overwrite(
    path: str,
    force_overwrite: bool = False,
    interaction_handler: Optional[InteractionHandler] = None,
) -> bool:
    """Whether `path` may be written: it does not exist, `force_overwrite` is
    set, or the user agrees.

    Args:
        path: The file to write.
        force_overwrite: Write without asking.
        interaction_handler: Asks the user. Defaults to the terminal.

    Raises:
        FileExistsError: If the file exists and there is no terminal to ask.
    """
    if force_overwrite or not os.path.isfile(path):
        return True
    if interaction_handler is None and not sys.stdin.isatty():
        raise FileExistsError(
            f"{path} already exists and there is no terminal to ask "
            "whether to overwrite it. Run bust with -f to overwrite it."
        )
    handler = interaction_handler or ConsoleInteractionHandler()
    if handler(f"Do you want to overwrite {path}? (y/N):").upper() != "Y":
        logger.warning(f"Did not write {path}")
        return False
    return True


def write_string_to_file(
    string: str,
    output_file: str,
    output_dir: str,
    force_overwrite: bool = False,
    interaction_handler: Optional[InteractionHandler] = None,
) -> bool:
    """Write string content to a file, asking first if it exists.

    Args:
        string: Content to write to file.
        output_file: Filename to write.
        output_dir: Directory path where file will be written.
        force_overwrite: Skip confirmation if file exists (default: False).
        interaction_handler: Asks whether to overwrite an existing file, see
            `may_overwrite`.

    Returns:
        True if file was written, False if user declined overwrite.

    Raises:
        RuntimeError: If output directory doesn't exist.
    """
    if not os.path.isdir(output_dir):
        raise RuntimeError(f"Output dir does not exist: {output_dir}")

    joined = os.path.join(output_dir, output_file)
    if not may_overwrite(joined, force_overwrite, interaction_handler):
        return False

    logger.debug(f"Writing string to {joined}")

    with open(joined, "w", encoding="utf-8") as strfile:
        strfile.write(string)
    return True
