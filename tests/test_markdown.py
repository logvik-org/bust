"""Descriptions in the Markdown documentation."""

from bust.jinja_utils.filters import align_markdown_tables, markdown_cell


def test_markdown_cell_escapes_markup_but_keeps_code():
    assert markdown_cell("a|b *c* <d>\n`x|y` [e]") == (r"a\|b \*c\* \<d\> `x\|y` \[e\]")


def test_align_markdown_tables_pads_columns_and_keeps_alignment():
    table = "| a | bb |\n|--:|---|\n| 100 | x |"
    assert align_markdown_tables(table) == (
        "|   a | bb  |\n" "| --: | --- |\n" "| 100 | x   |"
    )


def test_align_markdown_tables_keeps_escaped_pipes_in_their_cell():
    table = "| A | B |\n|---|---|\n| a\\|b | `x\\|y` |"
    assert align_markdown_tables(table).splitlines()[2] == "| a\\|b | `x\\|y` |"


def test_align_markdown_tables_leaves_other_lines_alone():
    text = "# Title\n\n| not a table |\nText"
    assert align_markdown_tables(text) == text
