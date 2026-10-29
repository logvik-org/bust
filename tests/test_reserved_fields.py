"""The documentation shows the bits that no field covers as reserved fields."""

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.generators.documentation_generator import DocumentationGenerator

_BUS = {"type": "axi", "addr_width": 8, "data_width": 32}

_CTRL = {
    "name": "ctrl",
    "sw": "rw",
    "hw": "r",
    "fields": [
        {"name": "enable", "type": "bit"},
        {"name": "mode", "type": "vector", "width": 2, "position": 4},
    ],
}

_COUNT = {"name": "count", "type": "vector", "width": 8, "sw": "rw", "hw": "r"}


def _module(*registers):
    config = {"name": "m", "register": list(registers or (_CTRL, _COUNT))}
    return Module(config, Bus(_BUS), settings=None)


def _ranges(register):
    return [
        (r.high, r.low, r.field.name if r.field else None) for r in register.bit_ranges
    ]


def test_bit_ranges_cover_every_bit_from_the_highest_down():
    ctrl, count = _module().registers

    assert _ranges(ctrl) == [
        (31, 6, None),
        (5, 4, "mode"),
        (3, 1, None),
        (0, 0, "enable"),
    ]
    assert _ranges(count) == [(31, 8, None), (7, 0, "count")]


def test_latex_documentation_lists_reserved_fields():
    pytest.importorskip("pylatexenc")
    tex = DocumentationGenerator(_module()).generate_tex_documentation("1.0.0")

    assert (
        "  \\regfield{reserved}{26}{6}{-}\n"
        "  \\regfield{mode}{2}{4}{{0x0}}\n"
        "  \\regfield{reserved}{3}{1}{-}\n"
        "  \\regfield{enable}{1}{0}{0}\n"
    ) in tex
    assert "  \\regfield{reserved}{24}{8}{-}\n  \\regfield{}{8}{0}" in tex
    assert (
        "    \\item [enable]  (sw: rw, hw: r)\n"
        "    \\item [reserved] Bits 3:1. Read as 0, writes have no effect.\n"
        "    \\item [mode]  (sw: rw, hw: r)\n"
        "    \\item [reserved] Bits 31:6. Read as 0, writes have no effect.\n"
    ) in tex
    assert "unused" not in tex


def test_html_documentation_lists_reserved_fields():
    page = DocumentationGenerator(_module()).generate_html_documentation("1.0.0")

    assert (
        "<dt>reserved</dt><dd>Bits 3:1. Read as 0, writes have no effect.</dd>" in page
    )
    assert ">reserved</text>" in page
    assert ">unused</text>" not in page


def test_markdown_documentation_lists_reserved_fields():
    page = DocumentationGenerator(_module()).generate_markdown_documentation("1.0.0")

    assert (
        "| 31:6 | reserved | | | | Read as 0, writes have no effect. |\n"
        "| 5:4 | mode |"
    ) in page
    assert "| 3:1 | reserved | | | | Read as 0, writes have no effect. |\n" in page


def test_markdown_documentation_lists_bits_below_the_lowest_field():
    irq = {"name": "irq", "fields": [{"name": "done", "type": "bit", "position": 2}]}
    page = DocumentationGenerator(_module(irq)).generate_markdown_documentation("1.0.0")

    assert "| 1:0 | reserved | | | | Read as 0, writes have no effect. |\n" in page


def test_the_editor_overview_shows_reserved_fields():
    pytest.importorskip("textual")
    from bust.editor.diagram import bit_diagram, field_notes

    ctrl = _module().registers[0]

    names = bit_diagram(ctrl, 32)[2]
    assert [name.strip() for name in names.split("│")[1:-1]] == [
        "reserved",
        "mode",
        "reserved",
        "enable",
    ]
    assert [name for name, _ in field_notes(ctrl)] == [
        "enable",
        "reserved",
        "mode",
        "reserved",
    ]
