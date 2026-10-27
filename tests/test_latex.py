"""Descriptions in the LaTeX and HTML documentation."""

import pytest


def test_description_code_and_unknown_characters():
    pytest.importorskip("pylatexenc")
    from bust.jinja_utils.filters import utf8tolatex

    assert utf8tolatex("⚠️ Write `ctrl_reg` & 50% é") == (
        r" Write \texttt{ctrl{\_}reg} {\&} 50{\%} {\'e}"
    )


def test_html_description_escapes_and_keeps_code():
    from bust.jinja_utils.filters import utf8tohtml

    assert utf8tohtml("⚠️ Write `a<b` & <i>") == (
        "⚠️ Write <code>a&lt;b</code> &amp; &lt;i&gt;"
    )
