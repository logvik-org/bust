"""Settings and bus keys: what bust uses, and what it keeps but ignores."""

import pytest

from bust.core.bus import Bus
from bust.exceptions import FormatError
from bust.settings import Settings


def test_missing_settings_section_uses_defaults():
    settings = Settings("cfg/m.json", None)

    assert settings.project_path == "cfg"
    assert settings.mod_subdir is True
    assert settings.to_json() == {"mod_subdir": True}


def test_proj_dir_sets_the_output_directory():
    settings = Settings("cfg/m.json", {"proj_dir": "out", "mod_subdir": False})

    assert settings.project_path == "out"
    assert settings.mod_subdir is False


def test_ignored_settings_are_written_back_unchanged():
    old = {"bus_subdir": False, "uvvm_rel_path": "../UVVM", "coverage": True}

    assert Settings("m.json", old).to_json() == dict(mod_subdir=True, **old)


def test_ignored_bus_keys_are_written_back_and_none_added():
    plain = {"type": "apb", "addr_width": 16, "data_width": 32}
    old = dict(plain, comp_library="regs", reset="async")

    assert Bus(plain).to_json() == plain
    assert Bus(old).to_json() == old


def test_data_width_must_be_whole_bytes():
    with pytest.raises(FormatError, match="whole number of bytes"):
        Bus({"type": "axi", "addr_width": 32, "data_width": 12})
