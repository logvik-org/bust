"""Regenerating over a bust 0.14 output tree must not destroy user logic.

bust 0.14 kept user logic in the top-level <module>.vhd between marker comments
and `-f` left that file alone. bust 1.0 regenerates the top as a fixed wrapper,
so generation stops instead of overwriting a top that still has the markers."""

import os
import subprocess
import sys

import pytest

from bust.core.bus import Bus
from bust.core.module import Module
from bust.exceptions import LegacyTopLevelFile
from bust.generation import generate_output
from bust.settings import Settings
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLE_JSON = os.path.join(_REPO_ROOT, "example", "example_axi.json")

_LEGACY_TOP = """\
library ieee;
use ieee.std_logic_1164.all;
-- User Libraries Start

-- User Libraries End

architecture rtl of example_axi is
  -- User Architecture Start
  signal counter : unsigned(7 downto 0);
  -- User Architecture End
begin
  -- User Logic Start
  counter <= counter + 1 when rising_edge(clk);
  -- User Logic End
end architecture rtl;
"""


def _hdl_dir(out_dir):
    return os.path.join(str(out_dir), "example_axi", "hdl")


def _write_top(out_dir, text):
    os.makedirs(_hdl_dir(out_dir))
    top = os.path.join(_hdl_dir(out_dir), "example_axi.vhd")
    with open(top, "w") as fp:
        fp.write(text)
    return top


def _generate(out_dir):
    cfg = json_parser(_EXAMPLE_JSON)
    settings = Settings(_EXAMPLE_JSON, cfg["settings"])
    bus = Bus(cfg["bus"])
    gen_settings = {
        "dir": str(out_dir),
        "force_ow": True,
        "gen_doc": False,
        "gen_pdf": False,
        "gen_header": False,
        "gen_localbus": True,
    }
    module = Module(cfg["module"], bus, settings)
    generate_output(settings, bus, module, None, None, gen_settings)


def test_legacy_top_with_user_markers_is_not_overwritten(tmp_path):
    top = _write_top(tmp_path, _LEGACY_TOP)

    with pytest.raises(LegacyTopLevelFile, match="delete or rename it to proceed"):
        _generate(tmp_path)

    with open(top) as fp:
        assert fp.read() == _LEGACY_TOP
    assert os.listdir(_hdl_dir(tmp_path)) == ["example_axi.vhd"]
    assert not os.path.exists(os.path.join(str(tmp_path), "example_axi", "tb"))


def test_top_without_user_markers_is_overwritten(tmp_path):
    top = _write_top(tmp_path, "-- an older generated wrapper\n")

    _generate(tmp_path)

    with open(top) as fp:
        assert "entity example_axi is" in fp.read()


def test_cli_exits_nonzero_on_legacy_top(tmp_path):
    top = _write_top(tmp_path, _LEGACY_TOP)

    result = subprocess.run(
        [sys.executable, "-m", "bust", _EXAMPLE_JSON, "-o", str(tmp_path), "-f"],
        cwd=str(tmp_path),
        env=dict(
            os.environ,
            PYTHONPATH=os.pathsep.join(
                filter(None, [_REPO_ROOT, os.environ.get("PYTHONPATH")])
            ),
        ),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "to_hw/from_hw" in result.stderr
    with open(top) as fp:
        assert fp.read() == _LEGACY_TOP
