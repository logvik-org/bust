"""Contract over the field-level access-mode combination space.

Every combination of field properties is either rejected by validation with an
error naming the field and register, or renders a regfile package, regfile and
AXI testbench whose record members, enum types and bit types line up. The whole
space is validated; generation runs on a pairwise-covering subset of the
accepted combinations, since rendering all of them takes minutes.

No VHDL compiler runs here, so the generated text is checked for the shape
errors that a compiler would report: references to record members that do not
exist, and assignments or aggregates that mix records, enums and bit types.
"""

import itertools
import re
from typing import Dict, Iterator, List, Optional, Tuple

import pytest

from bust.core.bus import Bus
from bust.core.field import Field
from bust.core.module import Module
from bust.exceptions import InvalidFieldFormat
from bust.generators.factory import GeneratorFactory

AXES: Dict[str, list] = {
    "sw": ["rw", "ro", "wo", "na"],
    "hw": ["r", "w", "rw", "na"],
    "onread": [None, "rclr", "rset"],
    "onwrite": [None, "woset", "woclr", "wot", "wzs", "wzc", "wzt", "wclr", "wset"],
    "singlepulse": [False, True],
    "write_enable": [None, "we", "wel"],
    "hw_set_clear": [None, "hwset", "hwclr", "both"],
    "sw_strobe": [None, "swmod", "swacc", "both"],
    "enum": [False, True],
    "type": ["bit", "vector"],
}

Combo = Tuple[Tuple[str, object], ...]


def _all_combos() -> Iterator[Combo]:
    for values in itertools.product(*AXES.values()):
        yield tuple(zip(AXES, values))


def _field_config(combo: Combo, name: str = "f") -> Dict:
    props = dict(combo)
    cfg: Dict = {
        "name": name,
        "type": props["type"],
        "sw": props["sw"],
        "hw": props["hw"],
    }
    if props["type"] == "vector":
        cfg["width"] = 3
    for key in ("onread", "onwrite"):
        if props[key]:
            cfg[key] = props[key]
    if props["singlepulse"]:
        cfg["singlepulse"] = True
    if props["write_enable"]:
        cfg[props["write_enable"]] = True
    for key in ("hwset", "hwclr"):
        if props["hw_set_clear"] in (key, "both"):
            cfg[key] = True
    for key in ("swmod", "swacc"):
        if props["sw_strobe"] in (key, "both"):
            cfg[key] = True
    if props["enum"]:
        cfg["enums"] = [
            {"name": "DISABLED", "value": 0},
            {"name": "ENABLED", "value": 1},
        ]
    return cfg


def _build_field(combo: Combo) -> Optional[Field]:
    """The field the combination builds, or None when validation rejects it."""
    try:
        return Field(_field_config(combo), 0, "reg")
    except InvalidFieldFormat as exc:
        assert str(exc).endswith("(field f in reg reg)"), str(exc)
        return None


def _unrenderable(field: Field) -> List[str]:
    """Why the templates could not render `field`; empty when they can."""
    reasons = []
    bit_effects = (field.onread, field.onwrite, field.singlepulse)
    if field.is_enum and (any(bit_effects) or field.hwset or field.hwclr):
        reasons.append("enum with a bit-level side effect or hwset/hwclr")
    if (field.swmod or field.swacc or field.singlepulse) and not field.hw_readable:
        reasons.append("to_hw strobe on a field missing from to_hw")
    if field.singlepulse and (field.hw_writes_continuously or field.onread):
        reasons.append("singlepulse with a continuous hw write or onread")
    return reasons


_ACCEPTED = [combo for combo in _all_combos() if _build_field(combo) is not None]


def test_validation_accepts_only_renderable_combinations():
    assert _ACCEPTED, "validation must leave some combinations"
    for combo in _ACCEPTED:
        reasons = _unrenderable(_build_field(combo))
        assert not reasons, (dict(combo), reasons)


# Derived field properties the templates branch on. Covering their pairs too
# reaches shapes that need several inputs at once, e.g. an enum constant (no
# state) next to other enums.
_TEMPLATE_BRANCHES = (
    "holds_state",
    "hw_writes_continuously",
    "to_hw_is_record",
    "from_hw_is_record",
)


def _pairwise_cover(combos: List[Combo]) -> List[Combo]:
    """Greedy subset in which every pair of property values (inputs and template
    branches) occurring in `combos` occurs at least once. Pair sets are bitmasks
    so scoring stays cheap."""
    index: Dict[Tuple, int] = {}
    masks = []
    for combo in combos:
        field = _build_field(combo)
        branches = tuple((name, getattr(field, name)) for name in _TEMPLATE_BRANCHES)
        mask = 0
        for pair in itertools.combinations(combo + branches, 2):
            mask |= 1 << index.setdefault(pair, len(index))
        masks.append(mask)
    uncovered = (1 << len(index)) - 1
    chosen = []
    while uncovered:
        best = max(
            range(len(combos)), key=lambda i: bin(masks[i] & uncovered).count("1")
        )
        chosen.append(combos[best])
        uncovered &= ~masks[best]
    return chosen


_PAIRWISE = _pairwise_cover(_ACCEPTED)


def _module(registers: List[Dict]) -> Module:
    bus = Bus({"type": "axi", "addr_width": 32, "data_width": 32})
    return Module({"name": "m", "register": registers}, bus, settings=None)


def _single_field_registers() -> List[Dict]:
    return [
        {"name": f"r{i}", "type": "fields", "fields": [_field_config(combo)]}
        for i, combo in enumerate(_PAIRWISE)
    ]


def _mixed_registers(per_register: int = 3) -> List[Dict]:
    """The pairwise combinations packed several to a register, so register-level
    test predictions see fields of different kinds side by side."""
    registers = []
    for start in range(0, len(_PAIRWISE), per_register):
        group = _PAIRWISE[start : start + per_register]
        fields = [_field_config(c, f"f{i}") for i, c in enumerate(group)]
        registers.append({"name": f"r{start}", "type": "fields", "fields": fields})
    return registers


class _Shapes:
    """Record members, enum literals and decode return types of a regfile package."""

    def __init__(self, module_name: str, pkg: str) -> None:
        self.roots = {
            root: f"t_{module_name}_{root}" for root in ("regs", "to_hw", "from_hw")
        }
        self.records = {
            name: dict(
                line.strip().rstrip(";").split(" : ")
                for line in body.strip().splitlines()
            )
            for name, body in re.findall(
                r"type (\w+) is record\n(.*?)end record;", pkg, re.S
            )
        }
        self.enums = {
            name: [lit.strip() for lit in lits.split(",")]
            for name, lits in re.findall(r"type (\w+) is \(([^)]*)\);", pkg)
        }
        self.decoders = dict(
            re.findall(r"function (to_\w+)\(s : [^;]*?\) return (\w+);", pkg)
        )

    def resolve(self, path: str) -> str:
        root, *members = path.split(".")
        rtype = self.roots[root]
        for member in members:
            assert member in self.records.get(
                rtype, {}
            ), f"{path}: no {member} in {rtype}"
            rtype = self.records[rtype][member]
        return rtype

    def rhs_type(self, rhs: str) -> Optional[str]:
        """Type of the expression forms the templates emit; None for bit-typed
        literals, slices and operators, which a bit target accepts as is."""
        if re.fullmatch(r"(regs|to_hw|from_hw)(\.\w+)+", rhs):
            return self.resolve(rhs)
        qualified = re.fullmatch(r"(t_\w+)'\((\w+)\)", rhs)
        if qualified:
            assert qualified.group(2) in self.enums[qualified.group(1)], rhs
            return qualified.group(1)
        decoder = re.fullmatch(r"(to_\w+)\(.*\)", rhs)
        if decoder and decoder.group(1) in self.decoders:
            return self.decoders[decoder.group(1)]
        return None

    def check(self, target: str, rhs: str, where: str) -> None:
        rhs = " ".join(rhs.split())
        if target in self.records and rhs.startswith("("):
            for item in _split_aggregate(rhs[1:-1]):
                member, value = (s.strip() for s in item.split("=>", 1))
                assert (
                    member in self.records[target]
                ), f"{where}: {member} not in {target}"
                self.check(self.records[target][member], value, f"{where}.{member}")
            return
        if target in self.enums and rhs in self.enums[target]:
            return
        actual = self.rhs_type(rhs)
        if target in self.records or target in self.enums or actual is not None:
            assert actual == target, f"{where}: {target} <= {rhs} ({actual})"


def _split_aggregate(body: str) -> List[str]:
    items, depth, current = [], 0, ""
    for char in body:
        depth += {"(": 1, ")": -1}.get(char, 0)
        if char == "," and depth == 0:
            items.append(current)
            current = ""
        else:
            current += char
    return items + [current]


def _check_generated_shapes(module: Module) -> None:
    pkg = GeneratorFactory.generate_regfile_package_vhdl(module)
    regfile = re.sub(r"--[^\n]*", "", GeneratorFactory.generate_regfile_vhdl(module))
    tb = re.sub(
        r"--[^\n]*", "", GeneratorFactory.generate_localbus_axi_testbench_vhdl(module)
    )
    shapes = _Shapes(module.name, pkg)

    for text in (regfile, tb):
        for path in re.findall(r"\b(?:regs|to_hw|from_hw)(?:\.\w+)+", text):
            shapes.resolve(path)
    for target, rhs in re.findall(
        r"^\s*((?:regs|to_hw|from_hw)(?:\.\w+)+) <= (.*);$", regfile + tb, re.M
    ):
        shapes.check(shapes.resolve(target), rhs, target)
    # Literal names repeat across enum types, so to_slv needs a typed argument.
    for argument in re.findall(r"to_slv\((.*?)\);", regfile):
        assert shapes.rhs_type(argument) in shapes.enums, f"to_slv({argument})"
    for rtype, aggregate in re.findall(
        r"constant \w+ : (\w+) := (\(.*?\));\n", pkg, re.S
    ):
        shapes.check(rtype, aggregate, "reset constant")
    for rtype, aggregate in re.findall(
        r"signal from_hw *: (\w+) := (\(.*?\));\n", tb, re.S
    ):
        shapes.check(rtype, aggregate, "testbench from_hw default")


@pytest.mark.parametrize(
    "registers", [_single_field_registers, _mixed_registers], ids=["single", "mixed"]
)
def test_pairwise_combinations_generate_consistent_vhdl(registers):
    _check_generated_shapes(_module(registers()))


def test_pairwise_cover_spans_every_accepted_value():
    for axis in AXES:
        accepted = {dict(c)[axis] for c in _ACCEPTED}
        assert accepted == {dict(c)[axis] for c in _PAIRWISE}, axis
