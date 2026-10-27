"""Descriptions in the Markdown documentation."""

from bust.jinja_utils.filters import markdown_cell


def test_markdown_cell_escapes_markup_but_keeps_code():
    assert markdown_cell("a|b *c* <d>\n`x|y` [e]") == (r"a\|b \*c\* \<d\> `x\|y` \[e\]")
