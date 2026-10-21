"""Addresses the generated testbench uses to check address decoding.

The testbench sets G_MODULE_ADDR_WIDTH a little wider than the registers need,
then checks that addresses where no register sits get an error response and
that writes to them change no register.
"""

from typing import TYPE_CHECKING, List, NamedTuple, Optional

if TYPE_CHECKING:
    from bust.core.module import Module
    from bust.core.register import Register


class UnmappedAddress(NamedTuple):
    """An address where no register sits, as the testbench writes it."""

    literal: str
    hex: str
    why: str


class AddressChecks:
    """The address decode settings and checks of a module's generated testbench.

    Args:
        module: The module the testbench drives.
    """

    def __init__(self, module: "Module"):
        self.module = module

    @property
    def module_addr_width(self) -> int:
        """G_MODULE_ADDR_WIDTH of the testbench.

        Two bits more than the registers need, so the testbench can check
        addresses above the registers, and no more than the address width.
        """
        return min(self.module.register_select_width + 2, int(self.module.addr_width))

    @property
    def alias_register(self) -> Optional["Register"]:
        """A register the testbench writes and reads back.

        The testbench reads it again after the writes to addresses without a
        register, to check that none of them reached it.
        """
        return next(
            (reg for reg in self.module.registers if reg.is_simple_readback), None
        )

    @property
    def unmapped_addresses(self) -> List[UnmappedAddress]:
        """Addresses where no register sits, each with why none answers there."""
        module = self.module
        stride = module.data_width // 8 if module.byte_addressable else 1
        span = 1 << module.register_select_width
        used = {reg.address for reg in module.registers}
        alias = self.alias_register
        alias_offset = alias.address if alias is not None else 0
        offsets = []
        gap = next((a for a in range(0, span, stride) if a not in used), None)
        if gap is not None:
            offsets.append((gap, "an unused register offset"))
        if stride > 1 and module.registers:
            inside = (alias or module.registers[0]).address + 1
            offsets.append((inside, "an address inside a register"))
        if self.module_addr_width > module.register_select_width:
            offsets.append((span + alias_offset, "an address above the registers"))
        if self.module_addr_width < module.addr_width:
            next_base = 1 << self.module_addr_width
            offsets.append((next_base + alias_offset, "another base address"))
        return [
            UnmappedAddress(
                literal=f'{module.addr_width}x"{offset:X}"',
                hex=f"0x{offset:X}",
                why=why,
            )
            for offset, why in offsets
        ]
