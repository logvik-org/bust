"""The generated VHDL follows the style in vsg.yaml.

The examples under example/ are the generator's output (test_suite.py keeps
them in step), so checking them checks the templates. The hand-written
reference HDL in hdl/prototype/ follows the same style.
"""

import glob
import json
import os
import subprocess
import sys

import pytest

pytest.importorskip("vsg")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PATTERNS = [
    "example/*/hdl/*.vhd",
    "example/*/tb/*.vhd",
    "hdl/prototype/*.vhd",
    "hdl/prototype/tb/*.vhd",
]


def test_vhdl_follows_the_style(tmp_path):
    files = sorted(
        path
        for pattern in _PATTERNS
        for path in glob.glob(os.path.join(_ROOT, pattern))
    )
    assert files
    report = tmp_path / "vsg.json"
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from vsg.__main__ import main; main()",
            "-ap",
            "-of",
            "summary",
            "-c",
            os.path.join(_ROOT, "vsg.yaml"),
            "-js",
            str(report),
            "-f",
            *files,
        ],
        stdout=subprocess.DEVNULL,
        check=False,
    )
    violations = [
        f"{os.path.relpath(f['file_path'], _ROOT)}:{v['linenumber']}: "
        f"{v['rule']} {v['solution']}"
        for f in json.loads(report.read_text())["files"]
        for v in f["violations"]
    ]
    assert not violations, "\n".join(violations)
