"""bust without the editor extra."""

import sys

import pytest

from bust.editor import run_editor


def test_the_editor_names_the_extra_when_textual_is_missing(tmp_path, monkeypatch):
    # None in sys.modules makes the import fail, as without Textual.
    monkeypatch.setitem(sys.modules, "bust.editor.app", None)

    with pytest.raises(ImportError, match=r"pip install 'bust\[editor\]'"):
        run_editor(str(tmp_path / "m.json"), create=True)

    assert not (tmp_path / "m.json").exists()
