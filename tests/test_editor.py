"""The interactive editor's register prompts, driven by scripted answers so no
curses menu or terminal is needed."""

from types import SimpleNamespace

from bust.core.bus import Bus
from bust.core.module import Module
from bust.editor import Editor


def _editor():
    editor = Editor.__new__(Editor)
    bus = Bus({"type": "axi", "addr_width": 32, "data_width": 32})
    editor.mod = Module({"name": "m", "register": []}, bus, settings=None)
    editor.menu = SimpleNamespace(subtitle="")
    editor.recently_saved = True
    return editor


def _answer(monkeypatch, answers):
    pending = list(answers)

    def scripted_input(prompt=""):
        assert pending, f"unexpected prompt: {prompt}"
        return pending.pop(0)

    monkeypatch.setattr("builtins.input", scripted_input)
    return pending


def test_add_register_at_a_manually_entered_address(monkeypatch):
    editor = _editor()
    pending = _answer(
        monkeypatch,
        [
            "ctrl",  # name
            "control register",  # description
            "",  # mode: default (rw)
            "n",  # no fields
            "",  # type: default
            "n",  # do not auto-assign the address
            "10",  # address in hex
            "",  # reset: default 0x0
            "",  # confirm
        ],
    )

    editor.add_register()

    assert pending == []
    (reg,) = editor.mod.registers
    assert (reg.name, reg.address) == ("ctrl", 0x10)
    assert editor.mod.addresses == [0x10]
