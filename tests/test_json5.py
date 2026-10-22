"""bust reads register maps written in JSON5 (#219)."""

from bust.core.bus import Bus
from bust.core.module import Module
from bust.utils.json_utils import json_parser
from tests.test_cli import _run_bust

_JSON5 = """{
  // A comment, a hexadecimal number and trailing commas.
  bus: {type: "axi", addr_width: 32, data_width: 32},
  module: {
    name: "m",
    register: [
      {name: "ctrl", address: 0x1c, reset: 0xFF, type: "vector", width: 8,},
    ],
  },
}
"""


def test_json5_file(tmp_path):
    path = tmp_path / "m.json5"
    path.write_text(_JSON5)

    cfg = json_parser(str(path))

    module = Module(cfg["module"], Bus(cfg["bus"]), settings=None)
    assert module.registers[0].address == 0x1C
    assert module.registers[0].reset == "0xff"


def test_save_addresses_keeps_the_json5_text(tmp_path):
    path = tmp_path / "m.json5"
    path.write_text(_JSON5.replace("address: 0x1c, ", ""))

    code, output = _run_bust(tmp_path, path.name, "-a", "-f")

    assert code == 0, output
    assert path.read_text() == _JSON5.replace("address: 0x1c, ", "").replace(
        "width: 8,}", 'width: 8, address: "0x0",}'
    )
