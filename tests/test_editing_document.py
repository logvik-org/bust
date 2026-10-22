"""RegisterMapDocument applies JSON Patch operations that bust accepts, and
writes the file only when the register map changed."""

import json
import os
import shutil

import pytest

from bust.editing.document import (
    EditRejected,
    FileChanged,
    RegisterMapDocument,
    diff_operations,
)
from bust.generators.factory import GeneratorFactory

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLES = sorted(
    name
    for name in os.listdir(os.path.join(_REPO_ROOT, "example"))
    if name.endswith(".json")
)
_BLINKY = os.path.join(_REPO_ROOT, "tests", "data", "migrate", "axi", "blinky.json")

_JSON5 = """{
  // An AXI module
  bus: {type: "axi", addr_width: 16, data_width: 32},
  module: {
    name: "m",
    register: [
      {name: "ctrl", address: 0x1c, sw: "rw", hw: "r", note: "kept"},
    ],
  },
}
"""


def _copy(tmp_path, source):
    path = tmp_path / os.path.basename(source)
    shutil.copyfile(source, path)
    return str(path)


def _example(tmp_path, name):
    return _copy(tmp_path, os.path.join(_REPO_ROOT, "example", name))


def _write(tmp_path, text, name="m.json5"):
    path = tmp_path / name
    path.write_bytes(text.encode("utf-8"))
    return str(path)


def _opened(path):
    document = RegisterMapDocument.open(path)
    document.check()
    return document


def _replace(path, value):
    return {"op": "replace", "path": path, "value": value}


@pytest.mark.parametrize("name", _EXAMPLES)
def test_saving_without_a_change_does_not_write(tmp_path, name):
    path = _example(tmp_path, name)
    os.utime(path, (0, 0))
    document = _opened(path)

    assert document.keeps_formatting
    assert not document.is_modified
    assert document.save(path) is False
    assert os.stat(path).st_mtime == 0


def test_a_change_and_its_undo_is_no_change(tmp_path):
    path = _example(tmp_path, "example_access_matrix.json")
    document = _opened(path)
    name = document.data["module"]["register"][0]["name"]

    document.apply([_replace("/module/register/0/name", "renamed")])
    assert document.is_modified
    document.apply([_replace("/module/register/0/name", name)])

    assert not document.is_modified
    assert document.save(path) is False


def test_save_changes_only_the_edited_value(tmp_path):
    path = _write(tmp_path, _JSON5)
    document = _opened(path)

    document.apply([_replace("/module/register/0/hw", "w")])

    assert document.save(path) is True
    with open(path, encoding="utf-8") as fp:
        assert fp.read() == _JSON5.replace('hw: "r"', 'hw: "w"')
    assert not document.is_modified


def test_save_keeps_crlf_line_endings(tmp_path):
    text = _JSON5.replace("\n", "\r\n")
    path = _write(tmp_path, text)
    document = _opened(path)

    document.apply([{"op": "add", "path": "/module/version", "value": "2"}])
    document.save(path)

    with open(path, "rb") as fp:
        assert fp.read().decode("utf-8") == text.replace(
            "    ],\r\n  },", '    ],\r\n    version: "2",\r\n  },'
        )


def test_setting_an_equal_value_keeps_how_it_is_written(tmp_path):
    document = _opened(_write(tmp_path, _JSON5))

    document.apply([_replace("/module/register/0/address", 0x1C)])

    assert document.text == _JSON5
    assert not document.is_modified


def test_a_rejected_change_keeps_the_document(tmp_path):
    document = _opened(_write(tmp_path, _JSON5))

    with pytest.raises(EditRejected, match="onread requires a software-readable"):
        document.apply(
            [
                _replace("/module/register/0/sw", "wo"),
                {"op": "add", "path": "/module/register/0/onread", "value": "rclr"},
            ]
        )

    assert document.text == _JSON5
    assert document.data["module"]["register"][0]["sw"] == "rw"
    assert not document.is_modified


@pytest.mark.parametrize(
    "operation, message",
    [
        (_replace("/module/register/5/sw", "ro"), "No value at /module/register/5"),
        ({"op": "move", "path": "/module/name"}, "Unknown operation 'move'"),
        ({"path": "/module/name"}, "Missing key: op"),
        (_replace("/bus/data_width", 12), "whole number of bytes"),
        (_replace("/module/register/0/name", "end"), "VHDL keyword"),
    ],
)
def test_bad_operations_are_rejected(tmp_path, operation, message):
    document = _opened(_write(tmp_path, _JSON5))

    with pytest.raises(EditRejected, match=message):
        document.apply([operation])
    assert document.text == _JSON5


def test_warnings_are_returned_and_not_logged(tmp_path, caplog):
    document = RegisterMapDocument.open(_write(tmp_path, _JSON5))

    warnings = document.check()

    assert warnings == [
        "module.register[0].note: bust does not know this key and ignores it"
    ]
    assert caplog.records == []


def test_a_file_the_scanner_reads_differently_is_rewritten_whole(tmp_path):
    # json5 reads the escaped key as "bus". The scanner keeps the raw text.
    text = _JSON5.replace("  bus:", "  \\u0062us:")
    path = _write(tmp_path, text)
    document = _opened(path)

    assert not document.keeps_formatting
    document.apply([_replace("/module/register/0/hw", "w")])
    document.save(path)

    with open(path, encoding="utf-8") as fp:
        assert json.load(fp)["module"]["register"][0]["hw"] == "w"


def test_save_refuses_a_file_changed_on_disk(tmp_path):
    path = _write(tmp_path, _JSON5)
    document = _opened(path)
    document.apply([_replace("/module/register/0/hw", "w")])
    _write(tmp_path, _JSON5 + "\n")

    with pytest.raises(FileChanged, match="changed after the editor read it"):
        document.save(path)


def test_a_new_register_map(tmp_path):
    path = str(tmp_path / "new.json")
    document = RegisterMapDocument.new(
        {"type": "apb", "addr_width": 8, "data_width": 32},
        {"name": "timer", "description": "", "version": "1.0"},
    )
    document.apply(
        [{"op": "add", "path": "/module/register/-", "value": {"name": "ctrl"}}]
    )

    assert document.is_modified
    assert document.save(path) is True
    with open(path, encoding="utf-8") as fp:
        assert json.load(fp)["module"]["register"] == [{"name": "ctrl"}]
    with pytest.raises(FileExistsError):
        RegisterMapDocument.new(
            {"type": "apb", "addr_width": 8, "data_width": 32}, {"name": "timer"}
        ).save(path)


def test_a_new_register_map_is_checked():
    with pytest.raises(EditRejected, match='"AXI" is not one of .*Did you mean "axi"'):
        RegisterMapDocument.new(
            {"type": "AXI", "addr_width": 8, "data_width": 32}, {"name": "m"}
        )


def test_next_free_address(tmp_path):
    document = _opened(_example(tmp_path, "example_axi.json"))

    assert document.next_free_address() == 0x30


def test_legacy_conversion_keeps_the_generated_hdl(tmp_path):
    document = _opened(_example(tmp_path, "example_axi.json"))
    old_module = document.module

    _, operations = document.legacy_conversion()
    document.apply(operations)

    registers = document.data["module"]["register"]
    assert list(registers[0]) == [
        "name",
        "sw",
        "hw",
        "type",
        "address",
        "reset",
        "description",
    ]
    assert (
        '"sw": "rw",\n                "hw": "r",\n                "type"'
        in document.text
    )
    for generate in (
        GeneratorFactory.generate_regfile_vhdl,
        GeneratorFactory.generate_regfile_package_vhdl,
    ):
        assert generate(document.module) == generate(old_module)
    assert document.legacy_conversion() == ([], [])


def test_legacy_conversion_of_a_file_bust_1_0_rejects(tmp_path):
    # Its address "10" is hexadecimal in bust 0.14 and not a multiple of 4 in 1.0.
    document = RegisterMapDocument.open(_copy(tmp_path, _BLINKY))
    with pytest.raises(EditRejected, match="Address 0xa of register clear"):
        document.check()

    changes, operations = document.legacy_conversion()
    document.apply(operations)

    assert changes[:3] == [
        "removed the settings section",
        "removed bus.comp_library",
        "enable: type is now bit",
    ]
    assert 'clear: address "10" is now "0x10"' in changes
    assert 'ctrl: mode rw is now sw "rw", hw "r"' in changes
    assert [reg.address for reg in document.module.registers] == [0x0, 0x4, 0x10]


def test_legacy_conversion_rejects_unsupported_timing(tmp_path):
    text = _JSON5.replace('sw: "rw", hw: "r"', 'mode: "pulse", pulse_cycles: 2')
    document = RegisterMapDocument.open(_write(tmp_path, text))

    with pytest.raises(EditRejected, match="pulse_cycles=2 is not supported"):
        document.legacy_conversion()


def test_diff_operations():
    old = {"a": 1, "b": [1, 2], "c": {"x": 1}, "d/e": 0}
    new = {"a": 2, "b": [1, 2, 3], "c": {"y": 1}, "d/e": 0, "f": True}

    assert diff_operations(old, new) == [
        {"op": "replace", "path": "/a", "value": 2},
        {"op": "replace", "path": "/b", "value": [1, 2, 3]},
        {"op": "remove", "path": "/c/x"},
        {"op": "add", "path": "/c/y", "value": 1},
        {"op": "add", "path": "/f", "value": True},
    ]


def test_every_schema_problem_is_in_the_message(tmp_path):
    document = _opened(_write(tmp_path, _JSON5))

    with pytest.raises(EditRejected) as error:
        document.apply(
            [
                {"op": "replace", "path": "/module/register/0/sw", "value": "rx"},
                {"op": "replace", "path": "/bus/addr_width", "value": "16 bits"},
            ]
        )

    assert str(error.value).splitlines() == [
        'bus.addr_width: must be a whole number such as 16, "0x10" or "0b10000" '
        "(got '16 bits')",
        'module.register[0].sw: "rx" is not one of "rw", "ro", "wo", "na". Did '
        'you mean "rw"?',
    ]
