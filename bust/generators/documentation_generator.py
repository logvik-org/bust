"""Documentation generation module for bust.

This module provides the DocumentationGenerator class for automatically generating
LaTeX, HTML and Markdown documentation from module definitions. The generated documentation
includes register maps, bit field descriptions, and access modes.
"""

from html import escape

from bust._version import __VERSION__
from bust.core.enums import RegisterType
from bust.generators.register_layout import (
    RESERVED_NOTE,
    bit_segments,
    bits_text,
    field_notes,
    register_heading,
    register_list,
)
from bust.jinja_utils.environment import render_template

# An estimate of a character's width at the 11px font of the names, enough to
# tell whether a name fits across its box or must be turned on its side.
_CHAR_WIDTH = 7
_NUMBERS_HEIGHT = 16
_RESET_HEIGHT = 18
_MIN_BOX_HEIGHT = 28


def bit_diagram_svg(register, data_width):
    """An inline SVG of the bits of `register`, laid out as the LaTeX register
    package draws them: a box per field with its name, the numbers of its
    highest and lowest bit above it, and its reset value below.

    A name too long for its box is turned on its side, and the boxes grow
    taller to fit the longest such name.
    """
    bit = 24 if data_width <= 32 else 14
    segments = bit_segments(register)
    is_turned = [len(s.name) * _CHAR_WIDTH + 6 > s.width * bit for s in segments]
    box_height = max(
        [_MIN_BOX_HEIGHT]
        + [
            len(s.name) * _CHAR_WIDTH + 10
            for s, turned in zip(segments, is_turned)
            if turned
        ]
    )
    width = data_width * bit
    box_top = _NUMBERS_HEIGHT
    height = box_top + box_height + _RESET_HEIGHT
    parts = [
        f'<svg class="bits" xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width + 2} {height}" width="{width + 2}" '
        f'role="img" aria-label="Bits of {escape(register.name)}">'
    ]
    x = 1
    for segment, turned in zip(segments, is_turned):
        w = segment.width * bit
        middle = x + w / 2
        name_y = box_top + box_height / 2
        if segment.width == 1:
            parts.append(_text(middle, box_top - 4, segment.high, "middle", "num"))
        else:
            parts.append(_text(x + 3, box_top - 4, segment.high, "start", "num"))
            parts.append(_text(x + w - 3, box_top - 4, segment.low, "end", "num"))
        css_class = "unused" if segment.is_unused else "field"
        parts.append(
            f'<rect class="{css_class}" x="{x}" y="{box_top}" '
            f'width="{w}" height="{box_height}"/>'
        )
        rotate = f' transform="rotate(-90 {middle} {name_y})"' if turned else ""
        parts.append(
            f'<text class="name" x="{middle}" y="{name_y}"{rotate} '
            f'text-anchor="middle" dominant-baseline="central">'
            f"{escape(segment.name)}</text>"
        )
        parts.append(_text(middle, height - 4, segment.reset, "middle", "reset"))
        x += w
    parts.append("</svg>")
    return "".join(parts)


def _text(x, y, text, anchor, css_class):
    return (
        f'<text class="{css_class}" x="{x}" y="{y}" '
        f'text-anchor="{anchor}">{escape(str(text))}</text>'
    )


class DocumentationGenerator:
    """Generates documentation for bus slave modules.

    The DocumentationGenerator class creates LaTeX, HTML and Markdown documentation with complete register
    specifications including addresses, bit positions, access modes, and
    descriptions.

    Attributes:
        module: Module instance to document.
    """

    def __init__(self, module):
        """Initialize Documentation generator.

        Args:
            module: Module instance to generate documentation for.
        """
        self.module = module

    def _render_template(self, template_name, version=None, **context):
        """Render a Jinja2 template with module context.

        Args:
            template_name: Path to template file relative to templates directory.
            version: Version string to include (default: current bust version).

        Returns:
            Rendered template content as string with trailing newline.
        """
        if version is None:
            version = __VERSION__

        headers, rows = register_list(self.module)
        return render_template(
            template_name,
            {
                "module": self.module,
                "version": version,
                "reg_type_fields": RegisterType.FIELDS,
                "list_headers": headers,
                "list_rows": list(zip(rows, self.module.registers)),
                "register_heading": register_heading,
                "bit_segments": bit_segments,
                "field_notes": field_notes,
                "bits_text": bits_text,
                "reserved_note": RESERVED_NOTE,
                **context,
            },
        )

    def generate_tex_documentation(self, test_version=None):
        """Generate LaTeX documentation for the module.

        Creates a complete LaTeX document with register map tables showing
        addresses, names, modes, bit positions, and descriptions.

        Args:
            test_version: Version string for testing (default: None, uses bust version).

        Returns:
            LaTeX document source code as string.
        """
        return self._render_template("latex/documentation.j2", test_version)

    def generate_html_documentation(self, test_version=None):
        """Generate the documentation as one self-contained HTML page.

        It follows the layout of the LaTeX documentation, with links from the
        register list and a sidebar to each register, and a print stylesheet.

        Args:
            test_version: Version string for testing (default: None, uses bust version).

        Returns:
            HTML document as string.
        """
        return self._render_template(
            "html/documentation.j2", test_version, bit_diagram_svg=bit_diagram_svg
        )

    def generate_markdown_documentation(self, test_version=None):
        """Generate Markdown documentation for the module, readable on GitHub.

        Args:
            test_version: Version string for testing (default: None, uses bust version).

        Returns:
            Markdown document as string.
        """
        return self._render_template("markdown/documentation.j2", test_version)
