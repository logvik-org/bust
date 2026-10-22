"""The interactive register map editor behind ``bust FILE -c`` and ``-e``.

The editor is a full-screen terminal application built on Textual. bust
imports Textual only when the editor starts, so generating code does not pay
for loading it.
"""

import os
from typing import List, Optional, Tuple

from bust.editing.document import Operation, RegisterMapDocument
from bust.editor.session import EditSession


def open_session(
    path: str, create: bool
) -> Tuple[Optional[EditSession], List[str], List[Operation]]:
    """Read the register map the editor starts from.

    Args:
        path: The register map file.
        create: True to start a new register map, which `path` must not hold.

    Returns:
        The register map, None to create one, and the changes and operations
        that convert a bust 0.14 file.

    Raises:
        FileExistsError: If `create` and `path` exists.
        EditRejected: If bust rejects the register map in `path`.
    """
    if create:
        if os.path.exists(path):
            raise FileExistsError(f"{path} exists. Edit it with bust {path} -e.")
        return None, [], []
    document = RegisterMapDocument.open(path)
    changes, operations = document.legacy_conversion()
    if not operations:
        document.check()
    return EditSession(document, path), changes, operations


def run_editor(path: str, create: bool) -> None:
    """Create or edit the register map in `path` until the user quits.

    Args:
        path: The register map file.
        create: True to start a new register map, which `path` must not hold.

    Raises:
        FileExistsError: If `create` and `path` exists.
        EditRejected: If bust rejects the register map in `path`.
        RuntimeError: If the editor stopped with a message.
    """
    session, changes, operations = open_session(path, create)
    from bust.editor.app import EditorApp

    app = EditorApp(path, session, changes, operations)
    app.run()
    if app.return_value is not None:
        raise RuntimeError(app.return_value)


__all__ = ["EditSession", "open_session", "run_editor"]
