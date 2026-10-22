"""The generated Python headers are already formatted by black.

The examples under example/ are the generator's output (test_suite.py keeps
them in step), so checking them checks the template.
"""

import glob
import os
import subprocess
import sys

import pytest

pytest.importorskip("black")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_python_headers_follow_black():
    files = sorted(glob.glob(os.path.join(_ROOT, "example/*/header/*.py")))
    assert files
    result = subprocess.run(
        [sys.executable, "-m", "black", "--check", "--diff", "--quiet", *files],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
