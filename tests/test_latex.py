"""Descriptions in the LaTeX documentation."""

import pytest


def test_description_code_and_unknown_characters():
    pytest.importorskip("pylatexenc")
    from bust.jinja_utils.filters import utf8tolatex

    assert utf8tolatex("⚠️ Write `ctrl_reg` & 50% é") == (
        r" Write \texttt{ctrl{\_}reg} {\&} 50{\%} {\'e}"
    )
