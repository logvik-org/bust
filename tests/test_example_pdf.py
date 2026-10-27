"""The example PDF in the documentation is rebuilt whenever prototype.tex
changes: the last commit that changed the PDF is no older than the last commit
that changed the .tex."""

import os
import shutil
import subprocess

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_TEX = os.path.join("example", "example_prototype", "doc", "prototype.tex")
_PDF = os.path.join("docs", "examples", "prototype.pdf")


def _last_commit_time(path):
    """The committer time, in seconds since the epoch, of the last commit that
    changed `path`."""
    output = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", path],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return int(output)


def test_example_pdf_is_committed_with_or_after_the_tex():
    if shutil.which("git") is None or not os.path.exists(
        os.path.join(_REPO_ROOT, ".git")
    ):
        pytest.skip("needs the git history of the repository")

    assert _last_commit_time(_PDF) >= _last_commit_time(_TEX), (
        f"{_TEX} changed after {_PDF} was last committed. "
        "Run scripts/make-example-pdf.sh and commit the PDF."
    )
