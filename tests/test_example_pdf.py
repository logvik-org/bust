"""The example PDF in the documentation is built from the current prototype.tex."""

import hashlib
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_TEX = os.path.join(_REPO_ROOT, "example", "example_prototype", "doc", "prototype.tex")
_RECORDED_SHA256 = os.path.join(_REPO_ROOT, "docs", "examples", "prototype.tex.sha256")


def test_example_pdf_is_built_from_the_current_tex():
    with open(_TEX, "rb") as fp:
        tex_sha256 = hashlib.sha256(fp.read()).hexdigest()
    with open(_RECORDED_SHA256) as fp:
        recorded_sha256 = fp.read().strip()

    assert tex_sha256 == recorded_sha256, (
        "prototype.tex changed since docs/examples/prototype.pdf was built. "
        "Run scripts/make-example-pdf.sh and commit the PDF."
    )
