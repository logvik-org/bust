"""The interactive register map editor behind ``bust FILE -c`` and ``-e``.

The editor is a full-screen terminal application built on Textual. bust
imports Textual only when the editor starts, so generating code does not pay
for loading it.
"""

import os
from typing import Optional

from bust.editing.document import RegisterMapDocument
from bust.editor.session import EditSession


def open_session(path: str, create: bool) -> Optional[EditSession]:
    """Read the register map the editor starts from.

    Args:
        path: The register map file.
        create: True to start a new register map, which `path` must not hold.

    Returns:
        The register map, or None to create one.

    Raises:
        FileExistsError: If `create` and `path` exists.
        EditRejected: If bust rejects the register map in `path`.
    """
    if create:
        if os.path.exists(path):
            raise FileExistsError(f"{path} exists. Edit it with bust {path} -e.")
        return None
    document = RegisterMapDocument.open(path)
    document.check()
    return EditSession(document, path)


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
    session = open_session(path, create)
    from bust.editor.app import EditorApp

    app = EditorApp(path, session)
    app.run()
    if app.return_value is not None:
        raise RuntimeError(app.return_value)


__all__ = ["EditSession", "open_session", "run_editor"]
