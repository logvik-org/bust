"""The register map overview: a register list and a bit diagram per register.

It follows the layout of the LaTeX documentation, drawn with box characters,
so the editor can show it in the terminal. Each bit of a register is a few
characters wide, and each field is a box over its bits with its name inside,
its reset value below and the numbers of its highest and lowest bit above. A
box is wider than its bits where its name would not fit.
"""

from dataclasses import dataclass
from typing import List, Tuple

from bust.core.enums import RegisterType
from bust.core.field import Field
from bust.core.module import Module
from bust.core.register import Register


@dataclass
class _Segment:
    name: str
    high: int
    low: int
    reset: str
    is_unused: bool = False

    @property
    def width(self) -> int:
        return self.high - self.low + 1


def _reset(text: str, width: int) -> str:
    value = int(text, 16)
    return str(value) if width < 2 else f"0x{value:X}"


def bit_segments(register: Register, unused_name: str = "unused") -> List[_Segment]:
    """The fields of `register` from the highest bit down, with the unused
    bits between them."""
    segments = []
    for bits in register.bit_ranges:
        if bits.field is None:
            segments.append(_Segment(unused_name, bits.high, bits.low, "-", True))
            continue
        name = (
            bits.field.name if register.type == RegisterType.FIELDS else register.name
        )
        reset = _reset(bits.field.reset, bits.width)
        segments.append(_Segment(name, bits.high, bits.low, reset))
    return segments


def _fit(text: str, width: int) -> str:
    return text.center(width)


def bit_width(data_width: int) -> int:
    """The number of characters each bit gets in a diagram."""
    return 3 if data_width <= 32 else 2


def unused_name(module: Module) -> str:
    """The name the diagrams give bits that no field covers."""
    return "reserved" if module.reserved_fields else "unused"


def bit_diagram(
    register: Register, data_width: int, unused: str = "unused"
) -> List[str]:
    """The lines of the bit diagram of `register`: bit numbers, the boxes with
    the field names, and the reset values. Bits that no field covers are
    named `unused`."""
    bit = bit_width(data_width)
    numbers = top = names = bottom = resets = ""
    for number, segment in enumerate(bit_segments(register, unused)):
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


def _access(register: Register) -> str:
    return f"{register.sw.value.upper()}/{register.hw.value.upper()}"


def register_list(module: Module) -> Tuple[List[str], List[List[str]]]:
    """The headings and rows of the register list."""
    headers = ["#", "Name", "SW/HW", "Address", "Type", "Width", "Reset"]
    rows = [
        [
            str(index),
            reg.name,
            _access(reg),
            f"0x{reg.address:08X}",
            reg.type.value.upper(),
            str(reg.width),
            f"0x{int(reg.reset, 16):X}",
        ]
        for index, reg in enumerate(module.registers)
    ]
    return headers, rows


def register_heading(register: Register) -> Tuple[str, str]:
    """The name and access, and the address, as the documentation heads a
    register."""
    return f"{register.name} - {_access(register)}", f"0x{register.address:08X}"


RESERVED_NOTE = "Read as 0, writes have no effect."


def _bits(high: int, low: int) -> str:
    return f"{high}:{low}" if high > low else str(low)


def _field_note(field: Field) -> str:
    keys = [f"sw: {field.sw.value}", f"hw: {field.hw.value}"]
    if field.onread:
        keys.append(f"onread: {field.onread.value}")
    if field.onwrite:
        keys.append(f"onwrite: {field.onwrite.value}")
    if field.singlepulse:
        keys.append("singlepulse")
    text = f"({', '.join(keys)})"
    if field.is_enum:
        values = ", ".join(f"{e.name}={e.value}" for e in field.enums)
        text = f"({', '.join(keys)}; values: {values})"
    if field.description:
        text = f"{field.description} {text}"
    return text


def field_notes(
    register: Register, reserved_fields: bool = False
) -> List[Tuple[str, str]]:
    """Each field's name, and its description with its access, as the
    documentation lists them under a register, from the lowest bit up. With
    `reserved_fields`, the bits that no field covers are listed as reserved
    fields among them."""
    notes = []
    for bits in reversed(register.bit_ranges):
        if bits.field is not None:
            notes.append((bits.field.name, _field_note(bits.field)))
        elif reserved_fields:
            notes.append(
                ("reserved", f"Bits {_bits(bits.high, bits.low)}. {RESERVED_NOTE}")
            )
    return notes
