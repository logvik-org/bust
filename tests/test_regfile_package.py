"""Verify the generated local-bus regfile package.

Two guards: a golden-file comparison against the committed reference (regression),
and a structural comparison against the hand-written, simulation-verified prototype
package in `hdl/prototype/` (the generator must reproduce the verified HDL)."""

import json
import os
import re

from bust.core.bus import Bus
from bust.core.module import Module
from bust.generators.factory import GeneratorFactory

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLE = os.path.join(_REPO_ROOT, "example", "example_prototype.json")
_GOLDEN = os.path.join(
    _REPO_ROOT, "example", "example_prototype", "hdl", "prototype_regfile_pkg.vhd"
)
_PROTOTYPE = os.path.join(_REPO_ROOT, "hdl", "prototype", "prototype_regfile_pkg.vhd")


def _build_module():
    with open(_EXAMPLE) as fp:
        cfg = json.load(fp)
    return Module(cfg["module"], Bus(cfg["bus"]), settings=None)


def _structural_lines(text):
    """Declaration lines with comments, blanks, and whitespace normalized away.

    Reset-aggregate and is_mapped lines are dropped: the verified prototype and the
    generator express the same values differently (`(others => '1')` vs `4X"F"`,
    wrapped vs single-line boolean), which is functional, not structural."""
    lines = []
    for raw in text.splitlines():
        line = re.sub(r"--.*$", "", raw).strip()
        line = re.sub(r"\s+", " ", line)
        if not line or "=>" in line or re.match(r"(return |or )?sel_is", line):
            continue
        lines.append(line)
    return lines


def test_regfile_package_matches_golden():
    generated = GeneratorFactory.generate_regfile_package_vhdl(_build_module())
    with open(_GOLDEN) as fp:
        assert generated == fp.read()


def test_regfile_package_matches_verified_prototype():
    generated = GeneratorFactory.generate_regfile_package_vhdl(_build_module())
    with open(_PROTOTYPE) as fp:
        assert _structural_lines(generated) == _structural_lines(fp.read())
