"""The layout the documentation and the editor share: the register list, the
heading of each register, the fields of a register from the highest bit down,
and the notes listed under a register.

The LaTeX, HTML and Markdown documentation and the editor overview all build on
these, so they show the same values in the same form.
"""

from dataclasses import dataclass
from typing import List, Tuple

from bust.core.enums import RegisterType
from bust.core.field import Field
from bust.core.module import Module
from bust.core.register import Register


@dataclass
class BitSegment:
    name: str
    high: int
    low: int
    reset: str
    is_unused: bool = False

    @property
    def width(self) -> int:
        return self.high - self.low + 1


def reset_text(text: str, width: int) -> str:
    value = int(text, 16)
    return str(value) if width < 2 else f"0x{value:X}"


def bit_segments(register: Register) -> List[BitSegment]:
    """The fields of `register` from the highest bit down, with the bits no
    field covers between them as reserved."""
    segments = []
    for bits in register.bit_ranges:
        if bits.field is None:
            segments.append(BitSegment("reserved", bits.high, bits.low, "-", True))
            continue
        name = (
            bits.field.name if register.type == RegisterType.FIELDS else register.name
        )
        reset = reset_text(bits.field.reset, bits.width)
        segments.append(BitSegment(name, bits.high, bits.low, reset))
    return segments


def access_text(register: Register) -> str:
    return f"{register.sw.value.upper()}/{register.hw.value.upper()}"


def register_list(module: Module) -> Tuple[List[str], List[List[str]]]:
    """The headings and rows of the register list."""
    headers = ["#", "Name", "SW/HW", "Address", "Type", "Width", "Reset"]
    rows = [
        [
            str(index),
            reg.name,
            access_text(reg),
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
    return f"{register.name} - {access_text(register)}", f"0x{register.address:08X}"


RESERVED_NOTE = "Read as 0, writes have no effect."


def bits_text(high: int, low: int) -> str:
    return f"{high}:{low}" if high > low else str(low)


def field_note(field: Field) -> str:
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


def field_notes(register: Register) -> List[Tuple[str, str]]:
    """Each field's name, and its description with its access, as the
    documentation lists them under a register, from the lowest bit up, with
    the bits no field covers listed as reserved."""
    notes = []
    for bits in reversed(register.bit_ranges):
        if bits.field is not None:
            notes.append((bits.field.name, field_note(bits.field)))
        else:
            notes.append(
                ("reserved", f"Bits {bits_text(bits.high, bits.low)}. {RESERVED_NOTE}")
            )
    return notes
