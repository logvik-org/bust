"""bust writes into <output directory>/<module>/ (#227)."""

import pytest

from bust.core.bus import Bus
from bust.exceptions import FormatError
from bust.settings import Settings


def test_output_goes_next_to_the_json_file():
    assert Settings("cfg/m.json").project_path == "cfg"
    assert Settings("m.json").project_path == "."


def test_data_width_must_be_whole_bytes():
    with pytest.raises(FormatError, match="whole number of bytes"):
        Bus({"type": "axi", "addr_width": 32, "data_width": 12})
