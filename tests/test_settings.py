"""bust writes into <output directory>/<module>/ and no longer reads the
settings section or the bust 0.14 bus keys (#227)."""

import logging

import pytest

from bust.core.bus import Bus
from bust.exceptions import FormatError
from bust.settings import Settings


def test_output_goes_next_to_the_json_file():
    assert Settings("cfg/m.json", None).project_path == "cfg"
    assert Settings("m.json", None).project_path == "."


def test_settings_section_is_ignored_with_a_warning(caplog):
    with caplog.at_level(logging.WARNING):
        settings = Settings("cfg/m.json", {"mod_subdir": True, "coverage": True})

    assert settings.project_path == "cfg"
    assert "The settings section is ignored" in caplog.text


@pytest.mark.parametrize("section", [{"proj_dir": "out"}, {"mod_subdir": False}])
def test_settings_that_move_the_output_stop_bust(section):
    with pytest.raises(FormatError, match="run bust with -o instead"):
        Settings("cfg/m.json", section)


def test_0_14_bus_keys_are_unknown(caplog):
    plain = {"type": "apb", "addr_width": 16, "data_width": 32}

    with caplog.at_level(logging.WARNING):
        Bus(dict(plain, comp_library="regs", reset="async"))

    assert "Unknown key 'comp_library' in bus is ignored" in caplog.text


def test_data_width_must_be_whole_bytes():
    with pytest.raises(FormatError, match="whole number of bytes"):
        Bus({"type": "axi", "addr_width": 32, "data_width": 12})
