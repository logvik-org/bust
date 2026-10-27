"""<module>.vhd belongs to the user. bust writes a starter only when the file is
missing, does not replace it with -f, and replaces it with --replace-top, keeping
the old file. The documentation needs no pdflatex."""

import logging
import os
import sys

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.generation import generate_output
from bust.settings import Settings
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLE_JSON = os.path.join(_REPO_ROOT, "example", "example_axi.json")


def _hdl_dir(out_dir):
    return os.path.join(str(out_dir), "example_axi", "hdl")


def _write_top(out_dir, text):
    os.makedirs(_hdl_dir(out_dir))
    top = os.path.join(_hdl_dir(out_dir), "example_axi.vhd")
    with open(top, "w") as fp:
        fp.write(text)
    return top


def _generate(out_dir, force_ow=True, replace_top=False, gen_doc=False):
    cfg = json_parser(_EXAMPLE_JSON)
    settings = Settings(_EXAMPLE_JSON)
    bus = Bus(cfg["bus"])
    gen_settings = {
        "dir": str(out_dir),
        "force_ow": force_ow,
        "replace_top": replace_top,
        "gen_doc": gen_doc,
        "gen_pdf": gen_doc,
        "gen_header": False,
        "gen_localbus": True,
    }
    module = Module(cfg["module"], bus, settings)
    generate_output(settings, module, gen_settings)


def _read(path):
    with open(path) as fp:
        return fp.read()


def test_missing_top_gets_a_starter(tmp_path):
    _generate(tmp_path)

    top = _read(os.path.join(_hdl_dir(tmp_path), "example_axi.vhd"))
    assert "entity example_axi is" in top
    assert "i_endpoint : entity work.example_axi_axi_endpoint" in top
    assert "-- A starting point. Add your own logic." in top


def test_existing_top_is_kept_with_force(tmp_path, caplog):
    top = _write_top(tmp_path, "-- my own top level\n")

    with caplog.at_level(logging.INFO):
        _generate(tmp_path, force_ow=True)

    assert _read(top) == "-- my own top level\n"
    assert "run bust with --replace-top" in caplog.text
    assert os.path.isfile(
        os.path.join(_hdl_dir(tmp_path), "example_axi_axi_endpoint.vhd")
    )


def test_existing_top_is_kept_quietly_without_force(tmp_path, caplog):
    top = _write_top(tmp_path, "-- my own top level\n")

    with caplog.at_level(logging.INFO):
        _generate(tmp_path, force_ow=False)

    assert _read(top) == "-- my own top level\n"
    assert "--replace-top" not in caplog.text


def test_replace_top_keeps_the_old_file(tmp_path):
    top = _write_top(tmp_path, "-- my own top level\n")

    _generate(tmp_path, force_ow=True, replace_top=True)

    assert "entity example_axi is" in _read(top)
    assert _read(top + ".bak") == "-- my own top level\n"


def test_replace_top_without_a_terminal_asks_for_force(tmp_path, monkeypatch):
    top = _write_top(tmp_path, "-- my own top level\n")
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False)

    with pytest.raises(FileExistsError, match="--replace-top -f"):
        _generate(tmp_path, force_ow=False, replace_top=True)

    assert _read(top) == "-- my own top level\n"
    assert not os.path.exists(top + ".bak")


def test_docs_without_pdflatex_skip_only_the_pdf(tmp_path, monkeypatch, caplog):
    pytest.importorskip("pylatexenc")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))

    with caplog.at_level(logging.INFO):
        _generate(tmp_path, gen_doc=True)

    doc_dir = os.path.join(str(tmp_path), "example_axi", "doc")
    assert sorted(os.listdir(doc_dir)) == ["example_axi.html", "example_axi.tex"]
    assert "pdflatex is not on PATH, so bust skipped the PDF" in caplog.text
