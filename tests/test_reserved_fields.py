"""reserved_fields shows the bits that no field covers as reserved fields."""

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.exceptions import FormatError
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


def _module(**keys):
    config = {"name": "m", "register": [_CTRL, _COUNT], **keys}
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


def test_reserved_fields_is_off_by_default():
    assert _module().reserved_fields is False


@pytest.mark.parametrize("value", ["true", 1, None])
def test_reserved_fields_must_be_a_boolean(value):
    with pytest.raises(FormatError, match="reserved_fields must be true or false"):
        _module(reserved_fields=value)


def test_reserved_fields_does_not_change_the_hash():
    assert _module().regmap_hash_hex == _module(reserved_fields=True).regmap_hash_hex


def _latex(**keys):
    pytest.importorskip("pylatexenc")
    return DocumentationGenerator(_module(**keys)).generate_tex_documentation("1.0.0")


def test_documentation_marks_every_gap_unused():
    tex = _latex()

    assert (
        "  \\regfield{unused}{26}{6}{-}\n"
        "  \\regfield{mode}{2}{4}{{0x0}}\n"
        "  \\regfield{unused}{3}{1}{-}\n"
        "  \\regfield{enable}{1}{0}{0}\n"
    ) in tex
    assert "\\item [reserved]" not in tex


def test_documentation_lists_reserved_fields():
    tex = _latex(reserved_fields=True)

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


def test_the_editor_overview_shows_reserved_fields():
    pytest.importorskip("textual")
    from bust.editor.diagram import bit_diagram, field_notes, unused_name

    module = _module(reserved_fields=True)
    ctrl = module.registers[0]

    names = bit_diagram(ctrl, 32, unused_name(module))[2]
    assert [name.strip() for name in names.split("│")[1:-1]] == [
        "reserved",
        "mode",
        "reserved",
        "enable",
    ]
    assert [name for name, _ in field_notes(ctrl, module.reserved_fields)] == [
        "enable",
        "reserved",
        "mode",
        "reserved",
    ]
    assert [name for name, _ in field_notes(ctrl)] == ["enable", "mode"]


def test_html_documentation_lists_reserved_fields():
    html = DocumentationGenerator(_module(reserved_fields=True))
    page = html.generate_html_documentation("1.0.0")

    assert (
        "<dt>reserved</dt><dd>Bits 3:1. Read as 0, writes have no effect.</dd>" in page
    )
    assert ">reserved</text>" in page
    assert ">unused</text>" not in page
