"""generate_files renders in memory what the bust command line writes to disk."""

import glob
import json
import os
import sys

import pytest

from bust.__main__ import main
from bust.exceptions import FormatError
from bust.generation import generate_files

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLES = sorted(glob.glob(os.path.join(_REPO_ROOT, "example", "*.json")))


def _read(path):
    with open(path, encoding="utf-8") as fp:
        return fp.read()


def _files_written_by_cli(json_file, out_dir, monkeypatch):
    # In this process, so that the pinned version in conftest.py holds for the
    # CLI too.
    monkeypatch.setattr(sys, "argv", ["bust", json_file, "-o", str(out_dir), "-p"])
    with pytest.raises(SystemExit) as stop:
        main()
    assert stop.value.code == 0
    written = {}
    for root, _, names in os.walk(str(out_dir)):
        for name in names:
            path = os.path.join(root, name)
            key = os.path.relpath(path, str(out_dir)).replace(os.sep, "/")
            written[key] = _read(path)
    return written


@pytest.mark.parametrize("json_file", _EXAMPLES, ids=os.path.basename)
def test_outputs_equal_the_files_the_cli_writes(json_file, tmp_path, monkeypatch):
    assert generate_files(_read(json_file)) == _files_written_by_cli(
        json_file, tmp_path, monkeypatch
    )


def test_parsed_register_map_gives_the_same_outputs():
    json_file = os.path.join(_REPO_ROOT, "example", "example_axi.json")
    text = _read(json_file)

    assert generate_files(json.loads(text)) == generate_files(text)


def test_starter_top_level_is_included():
    json_file = os.path.join(_REPO_ROOT, "example", "example_axi.json")

    outputs = generate_files(_read(json_file))

    assert "entity example_axi is" in outputs["example_axi/hdl/example_axi.vhd"]


def test_schema_problems_are_raised_together():
    register_map = {
        "bus": {"type": "axi", "addr_width": 32, "data_width": 32},
        "module": {
            "name": "m",
            "register": [
                {"name": "a", "sw": "rx", "hw": "r", "type": "default"},
                {"name": "b", "sw": "rw", "hw": "q", "type": "default"},
            ],
        },
    }

    with pytest.raises(FormatError) as error:
        generate_files(register_map)

    assert "module.register[0].sw" in str(error.value)
    assert "module.register[1].hw" in str(error.value)


def test_text_that_does_not_parse_raises_format_error():
    with pytest.raises(FormatError):
        generate_files('{"bus": ')
