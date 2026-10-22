"""The interactive editor, driven by scripted answers so no terminal is needed.

Each answer comes with the start of the question it answers, so a test fails
at the first question the editor asks out of turn."""

import json
import os
import shutil

import json5
import pytest

from bust.editor import Editor

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_BLINKY = os.path.join(_REPO_ROOT, "tests", "data", "migrate", "axi", "blinky.json")

_TIMER = """{
  // A timer
  bus: {type: "axi", addr_width: 16, data_width: 32},
  module: {
    name: "timer",
    register: [
      {
        name: "ctrl",
        address: 0x0,
        type: "fields",
        sw: "rw",
        hw: "r",
        fields: [
          {name: "enable", type: "bit"}, // starts the timer
        ],
      },
      {name: "count", address: 0x4, type: "vector", width: 16, sw: "ro", hw: "w"},
    ],
  },
}
"""

# The main menu entries.
_LIST, _ADD, _EDIT, _REMOVE, _MODULE, _ADDRESSES, _SAVE, _QUIT = map(str, range(1, 9))


class _Answers:
    def __init__(self, *pairs):
        self.pending = list(pairs)

    def __call__(self, prompt):
        assert self.pending, f"unexpected question: {prompt!r}"
        expected, answer = self.pending.pop(0)
        assert prompt.startswith(expected), f"asked {prompt!r}, not {expected!r}"
        return answer


def _session(start, path, *pairs):
    """Run the editor through the answers and return what it showed."""
    answers = _Answers(*pairs)
    shown = []
    start(str(path), answers, shown.append).run()
    assert answers.pending == [], f"not asked: {answers.pending}"
    return shown


def _timer(tmp_path):
    path = tmp_path / "timer.json5"
    path.write_text(_TIMER)
    return path


def _registers(path):
    return json5.loads(path.read_text())["module"]["register"]


def test_create_a_register_map(tmp_path):
    path = tmp_path / "uart.json"

    shown = _session(
        Editor.create,
        path,
        ("Bus", ""),
        ("Address width", "16"),
        ("Data width", ""),
        ("Module name [uart]", ""),
        ("Version [1.0]", ""),
        ("Description", "UART registers"),
        ("Do addresses count bytes", ""),
        ("Add the first register now?", ""),
        ("Name", "ctrl"),
        ("Address [0x0]", "0x2"),
        ("Address [0x0]", "0x4"),
        ("Type", "fields"),
        ("Software access", ""),
        ("Hardware access", ""),
        ("Field name", "tx_en"),
        ("Field type", ""),
        ("Lowest bit [0]", ""),
        ("Software access", ""),
        ("Hardware access", ""),
        ("Reset value", ""),
        ("Description", "Enable transmit"),
        ("Add another field?", "y"),
        ("Field name", "parity"),
        ("Field type", "vector"),
        ("Lowest bit [1]", "4"),
        ("Width in bits", "40"),
        ("Width in bits", "2"),
        ("Software access", "ro"),
        ("Hardware access", "w"),
        ("Reset value", "0x7"),
        ("Reset value", "0x1"),
        ("Description", "Parity"),
        ("Add another field?", ""),
        ("Description", "Control"),
        ("Set more properties of ctrl", ""),
        ("Menu", _ADD),
        ("Name", "status"),
        ("Address [0x0]", ""),
        ("Type", "vector"),
        ("Width in bits", "8"),
        ("Software access", "na"),
        ("Hardware access", "na"),
        ("Software access", "ro"),
        ("Hardware access", "w"),
        ("Reset value", ""),
        ("Description", ""),
        ("Set more properties of status", ""),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    for message in (
        "Address 0x2 of register ctrl is not a multiple of 4",
        "Register width exceeded module data width",
        "Reset value does not match field: parity",
        "field has neither software nor hardware access",
        "Saved",
    ):
        assert any(message in line for line in shown), message
    expected = {
        "bus": {"type": "axi", "addr_width": 16, "data_width": 32},
        "module": {
            "name": "uart",
            "version": "1.0",
            "description": "UART registers",
            "byte_addressable": True,
            "register": [
                {
                    "name": "ctrl",
                    "address": "0x4",
                    "type": "fields",
                    "sw": "rw",
                    "hw": "r",
                    "fields": [
                        {
                            "name": "tx_en",
                            "type": "bit",
                            "position": 0,
                            "reset": "0x0",
                            "description": "Enable transmit",
                        },
                        {
                            "name": "parity",
                            "type": "vector",
                            "position": 4,
                            "width": 2,
                            "sw": "ro",
                            "hw": "w",
                            "reset": "0x1",
                            "description": "Parity",
                        },
                    ],
                    "description": "Control",
                },
                {
                    "name": "status",
                    "address": "0x0",
                    "type": "vector",
                    "width": 8,
                    "sw": "ro",
                    "hw": "w",
                    "reset": "0x0",
                    "description": "",
                },
            ],
        },
    }
    assert path.read_text() == json.dumps(expected, indent=4) + "\n"


def test_create_does_not_ask_the_data_width_of_ipbus_and_can_quit_unsaved(tmp_path):
    path = tmp_path / "m.json"

    _session(
        Editor.create,
        path,
        ("Bus", "ipbus"),
        ("Address width", ""),
        ("Module name", ""),
        ("Version", ""),
        ("Description", ""),
        ("Do addresses count bytes, not data words (byte_addressable)? (y/N)", ""),
        ("Add the first register now?", "n"),
        ("Menu", _QUIT),
        ("There are unsaved changes", "2"),
    )

    assert not path.exists()


def test_create_refuses_an_existing_file(tmp_path):
    path = _timer(tmp_path)

    with pytest.raises(FileExistsError, match="Edit it with bust"):
        Editor.create(str(path), _Answers())


def test_open_and_quit_without_a_change_does_not_write(tmp_path):
    path = tmp_path / "matrix.json"
    shutil.copyfile(
        os.path.join(_REPO_ROOT, "example", "example_access_matrix.json"), path
    )
    os.utime(path, (0, 0))

    _session(Editor.open, path, ("Menu", _LIST), ("Menu", _SAVE), ("Menu", _QUIT))

    assert os.stat(path).st_mtime == 0


def test_edit_register_keys_in_place(tmp_path):
    path = _timer(tmp_path)

    _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "count"),
        ("Change", "7"),
        ("New sw", "rw"),
        ("Change", "9"),
        ("New onread", "rclr"),
        ("Change", "18"),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    assert path.read_text() == _TIMER.replace(
        'sw: "ro", hw: "w"}', 'sw: "rw", hw: "w", onread: "rclr"}'
    )


def test_unset_a_key(tmp_path):
    path = _timer(tmp_path)

    _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "2"),
        ("Change", "8"),
        ("New hw", "5"),
        ("Change", "18"),
        ("Menu", _QUIT),
        ("There are unsaved changes", "1"),
    )

    assert path.read_text() == _TIMER.replace(', hw: "w"}', "}")


def test_a_rejected_change_is_shown_and_not_made(tmp_path):
    path = _timer(tmp_path)

    shown = _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "count"),
        ("Change", "10"),
        ("New onwrite", "woclr"),
        ("Change", "18"),
        ("Menu", _QUIT),
    )

    assert any(
        line.startswith("Not changed: ")
        and "onwrite requires a software-writable" in line
        for line in shown
    )
    assert path.read_text() == _TIMER


def test_fields_and_enumerated_values(tmp_path):
    path = _timer(tmp_path)

    shown = _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "ctrl"),
        ("Change", "16"),
        ("Fields", "1"),
        ("Field name", "mode"),
        ("Field type", "vector"),
        ("Lowest bit [1]", ""),
        ("Width in bits", ""),
        ("Software access", ""),
        ("Hardware access", ""),
        ("Reset value", ""),
        ("Description", "Mode"),
        ("Fields", "2"),
        ("Field", "mode"),
        ("Change", "18"),
        ("Enumerated values", "1"),
        ("Name", "ONCE"),
        ("Value [0]", ""),
        ("Enumerated values", "1"),
        ("Name", "RUN"),
        ("Value [1]", ""),
        ("Enumerated values", "2"),
        ("Value", "RUN"),
        ("Change", "2"),
        ("New value", "3"),
        ("Enumerated values", "3"),
        ("Value", "ONCE"),
        ("Enumerated values", "4"),
        ("Change", "19"),
        ("Fields", "3"),
        ("Field", "enable"),
        ("Remove field enable?", "y"),
        ("Fields", "4"),
        ("Change", "17"),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    # Removing ONCE would leave the reset of 0 without a name.
    assert any("matches no declared enum value" in line for line in shown)
    (ctrl, _) = _registers(path)
    assert ctrl["fields"] == [
        {
            "name": "mode",
            "type": "vector",
            "position": 1,
            "width": 2,
            "reset": "0x0",
            "description": "Mode",
            "enums": [{"name": "ONCE", "value": 0}, {"name": "RUN", "value": 3}],
        }
    ]
    assert "// starts the timer" not in path.read_text()
    assert "// A timer" in path.read_text()


def test_change_the_register_type(tmp_path):
    path = _timer(tmp_path)

    _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "count"),
        ("Change", "4"),
        ("New type", "fields"),
        ("Field name", "value"),
        ("Field type", "vector"),
        ("Lowest bit", ""),
        ("Width in bits", "16"),
        ("Software access", ""),
        ("Hardware access", ""),
        ("Reset value", ""),
        ("Description", ""),
        ("Add another field?", ""),
        ("Change", "17"),
        ("Menu", _SAVE),
        ("Menu", _EDIT),
        ("Register", "count"),
        ("Change", "4"),
        ("New type", "bit"),
        ("Remove the fields of count?", "y"),
        ("Change", "17"),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    (_, count) = _registers(path)
    assert count == {
        "name": "count",
        "address": 4,
        "type": "bit",
        "sw": "ro",
        "hw": "w",
        "reset": "0x0",
    }


def test_fields_inherit_the_register_access(tmp_path):
    path = _timer(tmp_path)

    _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "count"),
        ("Change", "4"),
        ("New type", "fields"),
        ("Field name", "value"),
        ("Field type", ""),
        ("Lowest bit", ""),
        ("Software access (sw) of the field [2]", ""),
        ("Hardware access (hw) of the field [2]", "rw"),
        ("Reset value", ""),
        ("Description", ""),
        ("Add another field?", ""),
        ("Change", "17"),
        ("Menu", _QUIT),
        ("There are unsaved changes", "1"),
    )

    (_, count) = _registers(path)
    assert count["fields"] == [
        {
            "name": "value",
            "type": "bit",
            "position": 0,
            "hw": "rw",
            "reset": "0x0",
            "description": "",
        }
    ]


def test_remove_a_register_and_fill_in_addresses(tmp_path):
    path = tmp_path / "m.json"
    register_map = {
        "bus": {"type": "axi", "addr_width": 8, "data_width": 32},
        "module": {
            "name": "m",
            "register": [{"name": "a"}, {"name": "b", "address": "0x8"}, {"name": "c"}],
        },
    }
    path.write_text(json.dumps(register_map, indent=4))

    _session(
        Editor.open,
        path,
        ("Menu", _ADDRESSES),
        ("Menu", _REMOVE),
        ("Register", "b"),
        ("Remove register b?", "y"),
        ("Menu", _ADDRESSES),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    assert _registers(path) == [
        {"name": "a", "address": "0x0"},
        {"name": "c", "address": "0x4"},
    ]


def test_edit_the_module_and_bus(tmp_path):
    path = _timer(tmp_path)

    _session(
        Editor.open,
        path,
        ("Menu", _MODULE),
        ("Change", "3"),
        ("New version", "2.0"),
        ("Change", "5"),
        ("New type", "apb"),
        ("Change", "8"),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    assert path.read_text() == _TIMER.replace('{type: "axi"', '{type: "apb"').replace(
        "    ],\n  },\n}", '    ],\n    version: "2.0",\n  },\n}'
    )


def test_convert_a_bust_0_14_file(tmp_path):
    path = tmp_path / "blinky.json"
    shutil.copyfile(_BLINKY, path)

    shown = _session(
        Editor.open,
        path,
        ("Convert it?", ""),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    assert '  - clear: address "10" is now "0x10"' in shown
    saved = json.loads(path.read_text())
    assert "settings" not in saved
    assert [r.get("mode") for r in saved["module"]["register"]] == [None] * 3
    assert [r["sw"] for r in saved["module"]["register"]] == ["rw", "ro", "wo"]


def test_declining_the_conversion_does_not_open_the_file(tmp_path):
    path = tmp_path / "blinky.json"
    shutil.copyfile(_BLINKY, path)
    text = path.read_text()
    answers = _Answers(("Convert it?", "n"))

    assert Editor.open(str(path), answers, [].append) is None
    assert answers.pending == []
    assert path.read_text() == text


def test_end_of_input_quits(tmp_path):
    path = _timer(tmp_path)
    shown = []

    def no_more_input(prompt):
        raise EOFError

    Editor.open(str(path), no_more_input, shown.append).run()

    assert shown[-1] == "\nNo more input. Unsaved changes are lost."


def test_edit_text_number_and_true_false_keys(tmp_path):
    path = _timer(tmp_path)

    _session(
        Editor.open,
        path,
        ("Menu", _EDIT),
        ("Register", "count"),
        ("Change", "2"),
        ("New description", "Counter"),
        ("Change", "5"),
        ("New width (Enter keeps it, - removes it) [16]", "0x8"),
        ("Change", "6"),
        ("New reset", ""),
        ("Change", "6"),
        ("New reset", "-"),
        ("Change", "14"),
        ("New hwset [3]", "1"),
        ("Change", "18"),
        ("Menu", _SAVE),
        ("Menu", _QUIT),
    )

    assert path.read_text() == _TIMER.replace(
        'width: 16, sw: "ro", hw: "w"}',
        'width: 8, sw: "ro", hw: "w", description: "Counter", hwset: true}',
    )
