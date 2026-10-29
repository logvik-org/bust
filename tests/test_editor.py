"""The full-screen editor, driven headless through Textual's pilot.

Each test runs the editor on a file, works the main screen with keys and fills
in the dialogs, and checks the text of the file afterwards."""

import asyncio
import json
import os
import shutil
import subprocess
import sys

import json5
import pytest

from textual.widgets import Button, DataTable, Input, Select, Static  # noqa: E402

from bust.editing.document import EditRejected  # noqa: E402
from bust.editor import open_session  # noqa: E402
from bust.editor.app import EditorApp, MainScreen  # noqa: E402
from bust.editor.diagram import bit_diagram  # noqa: E402
from bust.editor.overview import OverviewScreen  # noqa: E402
from bust.editor.screens import (  # noqa: E402
    NOT_SET,
    FormScreen,
    QuestionScreen,
    TextScreen,
)
from bust.schema import SCHEMA_URL  # noqa: E402

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


class _Editor:
    """Works the editor the way a user does, one step at a time."""

    def __init__(self, app, pilot):
        self.app = app
        self.pilot = pilot
        self.messages = []
        notify = app.notify

        def recorded(message, *args, **kwargs):
            self.messages.append(str(message))
            notify(message, *args, **kwargs)

        app.notify = recorded

    @property
    def screen(self):
        return self.app.screen

    @property
    def main(self):
        return self.app.main

    async def press(self, *keys):
        await self.pilot.press(*keys)
        await self.pilot.pause()

    async def answer(self, **answers):
        """Answer questions of the open dialog."""
        screen = self.screen
        assert isinstance(screen, FormScreen), screen
        for name, value in answers.items():
            screen.query_one(f"#{name}").value = value
            await self.pilot.pause()

    async def fill(self, **answers):
        """Answer questions of the open dialog and press OK."""
        await self.answer(**answers)
        await self.button("ok")

    async def button(self, name):
        self.screen.query_one(f"#{name}", Button).press()
        await self.pilot.pause()

    def error(self):
        return str(self.screen.query_one("#error", Static).render())

    async def select_register(self, name):
        names = [reg.name for reg in self.app.session.registers]
        await self._select("registers", names.index(name))

    async def select_field(self, name):
        register = self.app.session.registers[self.main.register]
        await self._select("fields", [f.name for f in register.fields].index(name))

    async def _select(self, table, row):
        widget = self.main.query_one(f"#{table}", DataTable)
        widget.focus()
        widget.move_cursor(row=row)
        await self.pilot.pause()

    async def edit(self, key):
        """Open the dialog for a key of the register or field in focus."""
        keys = [prop.key for prop in self.main.properties] + ["enums"]
        table = self.main.query_one("#properties", DataTable)
        table.focus()
        table.move_cursor(row=keys.index(key))
        await self.press("enter")


def _session(path, script, create=False):
    """Run the editor on `path` through `script` and return what it showed."""

    async def run():
        app = EditorApp(str(path), open_session(str(path), create))
        async with app.run_test(size=(160, 50)) as pilot:
            editor = _Editor(app, pilot)
            await pilot.pause()
            await script(editor)
            await pilot.pause()
        return editor

    return asyncio.run(run())


def _timer(tmp_path):
    path = tmp_path / "timer.json5"
    path.write_text(_TIMER)
    return path


def _registers(path):
    return json5.loads(path.read_text())["module"]["register"]


def test_create_a_register_map(tmp_path):
    path = tmp_path / "uart.json"

    async def script(editor):
        assert editor.screen.query_one("#name", Input).value == "uart"
        await editor.fill(addr_width="16", description="UART registers")
        # The editor asks for the first register at once.
        await editor.fill(name="ctrl", address="0x2", type="fields")
        assert "Address 0x2 of register ctrl is not a multiple of 4" in editor.error()
        await editor.fill(address="0x4", description="Control")
        await editor.fill(name="tx_en", description="Enable transmit")
        assert editor.screen.__class__ is MainScreen
        await editor.press("f")
        assert editor.screen.query_one("#position", Input).value == "1"
        await editor.fill(name="parity", type="vector", position="4", width="40")
        assert "Register width exceeded module data width" in editor.error()
        await editor.fill(width="2", sw="ro", hw="w", reset="0x7")
        assert "Reset value does not match field: parity" in editor.error()
        await editor.fill(reset="0x1", description="Parity")
        await editor.press("a")
        assert editor.screen.query_one("#address", Input).value == "0x0"
        await editor.fill(name="status", type="vector", width="8", sw="na", hw="na")
        assert "neither software nor hardware access" in editor.error()
        await editor.fill(sw="ro", hw="w")
        await editor.press("s")
        await editor.press("q")

    editor = _session(path, script, create=True)

    assert f"Saved {path}." in editor.messages
    expected = {
        "$schema": SCHEMA_URL,
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


def test_create_hides_the_data_width_of_ipbus_and_can_quit_unsaved(tmp_path):
    path = tmp_path / "m.json"

    async def script(editor):
        await editor.answer(bus="ipbus")
        assert not editor.screen.query_one("#row-data_width").display
        assert editor.screen.query_one("#byte_addressable", Select).value == "false"
        await editor.fill(addr_width="32")
        assert editor.app.session.document.module.data_width == 32
        await editor.press("escape")
        await editor.press("q")
        assert isinstance(editor.screen, QuestionScreen)
        await editor.button("discard")

    _session(path, script, create=True)

    assert not path.exists()


def test_cancelling_the_new_register_map_quits(tmp_path):
    path = tmp_path / "m.json"

    async def script(editor):
        await editor.press("escape")
        assert not editor.app.is_running

    _session(path, script, create=True)

    assert not path.exists()


def test_create_refuses_an_existing_file(tmp_path):
    path = _timer(tmp_path)

    with pytest.raises(FileExistsError, match="Edit it with bust"):
        open_session(str(path), create=True)


def test_open_and_quit_without_a_change_does_not_write(tmp_path):
    path = tmp_path / "matrix.json"
    shutil.copyfile(
        os.path.join(_REPO_ROOT, "example", "example_access_matrix.json"), path
    )
    os.utime(path, (0, 0))

    async def script(editor):
        await editor.press("down", "down", "s")
        assert "There are no changes to save." in editor.messages
        await editor.press("q")
        assert not editor.app.is_running

    _session(path, script)

    assert os.stat(path).st_mtime == 0


def test_edit_register_keys_in_place(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("sw")
        await editor.fill(value="rw")
        await editor.edit("onread")
        await editor.fill(value="rclr")
        await editor.press("ctrl+s")

    _session(path, script)

    assert path.read_text() == _TIMER.replace(
        'sw: "ro", hw: "w"}', 'sw: "rw", hw: "w", onread: "rclr"}'
    )


def test_unset_a_key(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("hw")
        await editor.fill(value=NOT_SET)
        await editor.press("q")
        await editor.button("save")
        assert not editor.app.is_running

    _session(path, script)

    assert path.read_text() == _TIMER.replace(', hw: "w"}', "}")


def test_a_rejected_change_is_shown_and_not_made(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("onwrite")
        await editor.fill(value="woclr")
        assert "onwrite requires a software-writable" in editor.error()
        await editor.press("escape")
        assert isinstance(editor.screen, MainScreen)
        await editor.press("q")
        assert not editor.app.is_running

    _session(path, script)

    assert path.read_text() == _TIMER


def test_fields_and_enumerated_values(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("ctrl")
        await editor.press("f")
        await editor.fill(name="mode", type="vector", description="Mode")
        await editor.select_field("mode")
        await editor.edit("enums")
        await editor.press("a")
        assert editor.screen.query_one("#value", Input).value == "0"
        await editor.fill(name="ONCE")
        await editor.press("a")
        await editor.fill(name="RUN")
        await editor.press("down")
        await editor.press("enter")
        await editor.fill(value="3")
        await editor.press("up", "delete")
        await editor.press("escape")
        await editor.select_field("enable")
        await editor.press("delete")
        await editor.button("remove")
        await editor.press("s")

    editor = _session(path, script)

    # Removing ONCE would leave the reset of 0 without a name.
    assert any("matches no declared enum value" in line for line in editor.messages)
    ctrl, _ = _registers(path)
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


def test_add_field_needs_a_fields_register(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.press("f")
        assert isinstance(editor.screen, MainScreen)
        assert "Change the type of the register first" in editor.messages[-1]

    _session(path, script)


def test_change_the_register_type(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("type")
        await editor.fill(type="fields")
        await editor.fill(name="value", type="vector", width="16")
        await editor.press("s")
        assert _registers(path)[1]["fields"][0]["width"] == 16
        await editor.edit("type")
        await editor.fill(type="bit")
        await editor.press("s")

    _session(path, script)

    _, count = _registers(path)
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

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("type")
        await editor.fill(type="fields")
        assert editor.screen.query_one("#sw", Select).value == "ro"
        assert editor.screen.query_one("#hw", Select).value == "w"
        await editor.fill(name="value", hw="rw")
        await editor.press("s")

    _session(path, script)

    _, count = _registers(path)
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

    async def script(editor):
        await editor.press("g")
        assert "Gave 2 registers their address." in editor.messages
        await editor.select_register("b")
        await editor.press("d")
        await editor.button("cancel")
        assert len(editor.app.session.registers) == 3
        await editor.press("delete")
        await editor.button("remove")
        await editor.press("g")
        assert "Every register has an address." in editor.messages
        await editor.press("s")

    _session(path, script)

    assert _registers(path) == [
        {"name": "a", "address": "0x0"},
        {"name": "c", "address": "0x4"},
    ]


def test_edit_the_module_and_bus(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.press("m")
        await editor.press("down", "down", "enter")
        await editor.fill(value="2.0")
        await editor.press("down", "down", "down", "enter")
        await editor.fill(value="apb")
        await editor.press("escape", "s")

    _session(path, script)

    assert path.read_text() == _TIMER.replace('{type: "axi"', '{type: "apb"').replace(
        "    ],\n  },\n}", '    ],\n    version: "2.0",\n  },\n}'
    )


def test_a_bust_0_14_file_is_not_opened(tmp_path):
    path = tmp_path / "blinky.json"
    shutil.copyfile(_BLINKY, path)

    with pytest.raises(EditRejected, match="Run bust with --migrate"):
        open_session(str(path), create=False)


def test_edit_text_number_and_true_false_keys(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("description")
        await editor.fill(value="Count")
        await editor.edit("description")
        await editor.button("remove")
        await editor.edit("width")
        await editor.fill(value="0x8")
        await editor.edit("reset")
        # Not set in the file, so there is nothing to remove.
        assert not editor.screen.query("#remove")
        await editor.press("escape")
        await editor.edit("description")
        await editor.fill(value="Counter")
        await editor.edit("hwset")
        await editor.fill(value="true")
        await editor.edit("width")
        await editor.fill(value="eight")
        assert "eight" in editor.error()
        await editor.press("escape", "s")

    _session(path, script)

    assert path.read_text() == _TIMER.replace(
        'width: 16, sw: "ro", hw: "w"}',
        'width: 8, sw: "ro", hw: "w", description: "Counter", hwset: true}',
    )


def test_a_file_changed_on_disk_is_not_saved(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("description")
        await editor.fill(value="Counter")
        path.write_text(_TIMER + "\n")
        await editor.press("s")
        assert any(m.startswith("Not saved: ") for m in editor.messages)

    _session(path, script)

    assert path.read_text() == _TIMER + "\n"


def test_add_a_hash_register(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.press("a")
        await editor.answer(type="hash")
        for name in ("width", "sw", "hw", "reset"):
            assert not editor.screen.query_one(f"#row-{name}").display
        await editor.fill(name="id_hash", description="Register map hash")
        assert [p.key for p in editor.main.properties] == [
            "name",
            "description",
            "address",
            "type",
        ]
        await editor.press("s")

    _session(path, script)

    assert _registers(path)[-1] == {
        "name": "id_hash",
        "address": "0x8",
        "type": "hash",
        "description": "Register map hash",
    }


def test_change_a_register_to_hash(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.select_register("count")
        await editor.edit("type")
        await editor.fill(type="hash")
        await editor.press("s")

    _session(path, script)

    _, count = _registers(path)
    assert count == {"name": "count", "address": 4, "type": "hash"}


def test_add_a_version_register(tmp_path):
    path = _timer(tmp_path)
    path.write_text(_TIMER.replace('name: "timer",', 'name: "timer", version: "1.2",'))

    async def script(editor):
        await editor.press("a")
        await editor.fill(name="id_version", type="version")
        await editor.press("s")

    _session(path, script)

    assert _registers(path)[-1] == {
        "name": "id_version",
        "address": "0x8",
        "type": "version",
        "description": "",
    }


def test_help_overview_and_pane_keys(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        await editor.press("3")
        assert editor.app.focused.id == "properties"
        await editor.press("2")
        assert editor.app.focused.id == "fields"
        await editor.press("question_mark")
        assert isinstance(editor.screen, TextScreen)
        await editor.press("escape", "o")
        assert isinstance(editor.screen, OverviewScreen)
        shown = "\n".join(
            str(widget.render()) for widget in editor.screen.query(".diagram")
        )
        assert "│ enable │" in shown
        await editor.press("down", "enter", "escape")
        assert isinstance(editor.screen, MainScreen)

    _session(path, script)


def test_bit_diagram():
    path = os.path.join(_REPO_ROOT, "example", "example_axi.json")
    session = open_session(path, create=False)
    reg3 = session.registers[3]

    lines = bit_diagram(reg3, 32)

    assert lines[2].split("│")[1:3] == [
        " " * 33 + "unused" + " " * 32,
        " " * 10 + "reg3" + " " * 9,
    ]
    assert lines[1].startswith("┌") and lines[1].endswith("┐")
    assert lines[0].split() == ["31", "8", "7", "0"]
    assert lines[4].split() == ["-", "0x3"]


def test_the_command_line_loads_textual_only_for_the_editor():
    code = "import sys, bust.__main__; print('textual' in sys.modules)"
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )

    assert result.stdout.strip() == "False"


def test_switch_between_light_and_dark(tmp_path):
    path = _timer(tmp_path)

    async def script(editor):
        assert editor.app.theme == "bust-dark"
        await editor.press("t")
        assert editor.app.theme == "bust-light"
        await editor.press("o", "t")
        assert editor.app.theme == "bust-dark"

    _session(path, script)
