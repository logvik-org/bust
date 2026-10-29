"""The register map overview: a register list and a bit diagram per register.

It follows the layout of the LaTeX documentation, drawn with box characters,
so the editor can show it in the terminal. Each bit of a register is a few
characters wide, and each field is a box over its bits with its name inside,
its reset value below and the numbers of its highest and lowest bit above. A
box is wider than its bits where its name would not fit.
"""

from typing import List

from bust.core.register import Register
from bust.generators.register_layout import bit_segments


def _fit(text: str, width: int) -> str:
    return text.center(width)


def bit_width(data_width: int) -> int:
    """The number of characters each bit gets in a diagram."""
    return 3 if data_width <= 32 else 2


def bit_diagram(register: Register, data_width: int) -> List[str]:
    """The lines of the bit diagram of `register`: bit numbers, the boxes with
    the field names, and the reset values."""
    bit = bit_width(data_width)
    numbers = top = names = bottom = resets = ""
    for number, segment in enumerate(bit_segments(register)):
        high, low = str(segment.high), str(segment.low)
        bits = high if segment.width == 1 else f"{high} {low}"
        # A box grows past its bits rather than cut a name short.
        inner = max(
            segment.width * bit - 1,
            len(segment.name) + 2,
            len(segment.reset) + 2,
            len(bits) + 2,
        )
        left_top, left_bottom = ("┌", "└") if number == 0 else ("┬", "┴")
        top += left_top + "─" * inner
        bottom += left_bottom + "─" * inner
        names += "│" + _fit(segment.name, inner)
        resets += " " + _fit(segment.reset, inner)
        if segment.width == 1:
            label = _fit(high, inner)
        else:
            label = " " + high.ljust(inner - len(low) - 2) + low + " "
        numbers += " " + label
    return [numbers, top + "┐", names + "│", bottom + "┘", resets]
