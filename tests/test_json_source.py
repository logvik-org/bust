"""JsonSource edits one value in the text of a JSON or JSON5 file and leaves
the rest of the text as it was. Each test compares the whole text."""

import glob
import json
import os

import pytest

from bust.editing.json_source import JsonSource, JsonSourceError, apply_to_data
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_REGISTER_MAPS = sorted(
    glob.glob(os.path.join(_REPO_ROOT, "example", "*.json"))
    + glob.glob(
        os.path.join(_REPO_ROOT, "tests", "data", "**", "*.json"), recursive=True
    )
)

_JSON = """{
    "bus": {
        "type": "axi"
    },
    "register": [
        {
            "name": "ctrl",
            "reset": "0x0"
        },
        {
            "name": "status"
        }
    ]
}
"""

_JSON5 = """// A register map
{
  bus: {type: 'axi', addr_width: 16, data_width: 32,},
  register: [
    // The control register
    {name: "ctrl", address: 0x0}, // first
    {name: "status", address: 0x4},
  ],
  empty: [],
}
"""


def _edited(text, method, *args):
    source = JsonSource(text)
    getattr(source, method)(*args)
    return source.text


@pytest.mark.parametrize(
    "path", _REGISTER_MAPS, ids=lambda p: os.path.relpath(p, _REPO_ROOT)
)
def test_value_matches_json_parser(path):
    with open(path, encoding="utf-8") as fp:
        source = JsonSource(fp.read())

    assert source.value == json_parser(path)


@pytest.mark.parametrize(
    "path", _REGISTER_MAPS, ids=lambda p: os.path.relpath(p, _REPO_ROOT)
)
def test_every_register_can_be_removed_and_added_back(path):
    with open(path, encoding="utf-8") as fp:
        text = fp.read()
    registers = JsonSource(text).value["module"]["register"]

    for index, register in enumerate(registers):
        source = JsonSource(text)
        source.remove(f"/module/register/{index}")
        source.add(f"/module/register/{index}", register)
        assert source.value["module"]["register"] == registers


def test_value_of_json5():
    assert JsonSource(_JSON5).value == {
        "bus": {"type": "axi", "addr_width": 16, "data_width": 32},
        "register": [
            {"name": "ctrl", "address": 0},
            {"name": "status", "address": 4},
        ],
        "empty": [],
    }


def test_replace_a_number_keeps_the_other_numbers_as_written():
    assert _edited(_JSON5, "replace", "/register/1/address", "0x8") == _JSON5.replace(
        "address: 0x4", 'address: "0x8"'
    )


def test_replace_a_string():
    assert _edited(_JSON, "replace", "/register/0/reset", "0x1") == _JSON.replace(
        '"reset": "0x0"', '"reset": "0x1"'
    )


def test_replace_a_list_with_a_longer_one():
    text = '{\n    "a": [1],\n    "b": 2\n}\n'

    assert (
        _edited(text, "replace", "/a", [1, 2]) == '{\n    "a": [1, 2],\n    "b": 2\n}\n'
    )


def test_add_a_key_to_an_object_with_one_key_per_line():
    assert _edited(_JSON, "add", "/register/1/sw", "ro") == _JSON.replace(
        '"name": "status"\n', '"name": "status",\n            "sw": "ro"\n'
    )


def test_add_a_key_before_another():
    assert _edited(_JSON, "add", "/register/0/sw", "ro", "reset") == _JSON.replace(
        '"reset": "0x0"', '"sw": "ro",\n            "reset": "0x0"'
    )


def test_apply_to_data_puts_a_key_before_another():
    data = {"name": "ctrl", "type": "bit"}

    apply_to_data(data, "add", "/sw", "rw", before="type")

    assert list(data.items()) == [("name", "ctrl"), ("sw", "rw"), ("type", "bit")]


def test_add_an_existing_key_replaces_its_value():
    assert _edited(_JSON, "add", "/bus/type", "apb") == _JSON.replace('"axi"', '"apb"')


def test_add_a_register_in_the_middle_of_a_list():
    new = {"name": "irq", "address": "0x8"}

    assert _edited(_JSON, "add", "/register/1", new) == _JSON.replace(
        '        {\n            "name": "status"',
        "        {\n"
        '            "name": "irq",\n'
        '            "address": "0x8"\n'
        "        },\n"
        "        {\n"
        '            "name": "status"',
    )


def test_add_a_register_at_the_end_of_a_list():
    assert _edited(_JSON, "add", "/register/-", {"name": "irq"}) == _JSON.replace(
        '            "name": "status"\n        }\n',
        '            "name": "status"\n'
        "        },\n"
        "        {\n"
        '            "name": "irq"\n'
        "        }\n",
    )


def test_add_above_the_comment_that_belongs_to_the_next_element():
    assert _edited(_JSON5, "add", "/register/0", {"name": "id"}) == _JSON5.replace(
        "    // The control register\n",
        '    {"name": "id"},\n    // The control register\n',
    )


def test_add_to_a_list_with_a_trailing_comma_keeps_it():
    assert _edited(_JSON5, "add", "/register/-", {"name": "irq"}) == _JSON5.replace(
        '{name: "status", address: 0x4},\n',
        '{name: "status", address: 0x4},\n    {"name": "irq"},\n',
    )


def test_add_after_an_element_with_a_comment_at_the_end_of_its_line():
    text = "[\n    1, // one\n    2 // two\n]\n"

    assert (
        _edited(text, "add", "/-", 3) == "[\n    1, // one\n    2, // two\n    3\n]\n"
    )


def test_add_to_an_inline_object_matches_unquoted_keys():
    assert _edited(_JSON5, "add", "/register/0/sw", "rw") == _JSON5.replace(
        "address: 0x0}", 'address: 0x0, sw: "rw"}'
    )


def test_add_to_an_inline_object_with_a_trailing_comma():
    assert _edited(_JSON5, "add", "/bus/x", 1) == _JSON5.replace(
        "data_width: 32,}", "data_width: 32, x: 1,}"
    )


def test_add_to_an_empty_list_indents_one_level_deeper():
    assert _edited(_JSON5, "add", "/empty/-", {"name": "a"}) == _JSON5.replace(
        "  empty: [],\n", '  empty: [\n    {\n      "name": "a"\n    }\n  ],\n'
    )


def test_add_to_an_empty_object():
    assert _edited('{\n    "a": {}\n}\n', "add", "/a/b", 1) == (
        '{\n    "a": {\n        "b": 1\n    }\n}\n'
    )


def test_add_keeps_crlf_line_endings():
    text = _JSON.replace("\n", "\r\n")

    assert _edited(text, "add", "/register/1/sw", "ro") == text.replace(
        '"name": "status"\r\n', '"name": "status",\r\n            "sw": "ro"\r\n'
    )


def test_add_keeps_tab_indentation():
    text = _JSON.replace("    ", "\t")

    assert _edited(text, "add", "/register/-", {"name": "irq"}) == text.replace(
        '\t\t\t"name": "status"\n\t\t}\n',
        '\t\t\t"name": "status"\n\t\t},\n\t\t{\n\t\t\t"name": "irq"\n\t\t}\n',
    )


def test_add_writes_plain_json_into_a_json_file():
    text = _edited(_JSON, "add", "/register/0/note", 'it\'s "quoted" é')

    assert json.loads(text)["register"][0]["note"] == 'it\'s "quoted" é'
    assert '"note": "it\'s \\"quoted\\" é"' in text


def test_remove_the_first_element_with_its_comment_line():
    assert _edited(_JSON5, "remove", "/register/0") == _JSON5.replace(
        '    // The control register\n    {name: "ctrl", address: 0x0}, // first\n', ""
    )


def test_remove_the_last_element_takes_the_comma_before_it():
    assert _edited(_JSON, "remove", "/register/1") == _JSON.replace(
        '        },\n        {\n            "name": "status"\n        }\n',
        "        }\n",
    )


def test_remove_the_last_key_of_an_object():
    assert _edited(_JSON, "remove", "/register/0/reset") == _JSON.replace(
        '"name": "ctrl",\n            "reset": "0x0"\n', '"name": "ctrl"\n'
    )


def test_remove_the_last_element_of_a_list_with_a_trailing_comma():
    assert _edited(_JSON5, "remove", "/register/1") == _JSON5.replace(
        '    {name: "status", address: 0x4},\n', ""
    )


def test_remove_from_an_inline_object():
    assert _edited(_JSON5, "remove", "/bus/type") == _JSON5.replace("type: 'axi', ", "")
    assert _edited(_JSON5, "remove", "/register/0/address") == _JSON5.replace(
        '"ctrl", address: 0x0}', '"ctrl"}'
    )


def test_remove_the_only_element_leaves_empty_brackets():
    assert _edited('{\n    "a": [\n        1\n    ]\n}\n', "remove", "/a/0") == (
        '{\n    "a": []\n}\n'
    )
    assert _edited('{"a": [ 1 ]}', "remove", "/a/0") == '{"a": []}'


def test_pointer_escapes():
    text = '{"a/b": 1, "c~d": 2}'

    assert _edited(text, "replace", "/a~1b", 3) == '{"a/b": 3, "c~d": 2}'
    assert _edited(text, "replace", "/c~0d", 3) == '{"a/b": 1, "c~d": 3}'


@pytest.mark.parametrize(
    "method, args, message",
    [
        ("replace", ("/missing", 1), "No value at /missing"),
        ("replace", ("/register/2/name", "x"), "No value at /register/2"),
        ("replace", ("/register/x", 1), "No list position at /register/x"),
        ("replace", ("/bus/type/x", 1), "No object or list holds /bus/type/x"),
        ("add", ("/register/3", {}), "No list position at /register/3"),
        ("remove", ("",), "The whole document cannot be added or removed"),
        ("remove", ("bus",), "A path starts with '/'"),
    ],
)
def test_bad_paths_raise_and_leave_the_text(method, args, message):
    source = JsonSource(_JSON)

    with pytest.raises(JsonSourceError, match=message):
        getattr(source, method)(*args)
    assert source.text == _JSON


@pytest.mark.parametrize(
    "text, message",
    [
        ('{"a": "b}', "Line 1: unterminated string"),
        ('{"a": 1\n "b": 2}', "Line 2: expected ',' or '}'"),
        ("{\n/* open", "Line 2: unterminated comment"),
        ('{"a": 1} x', "text after the end of the document"),
        ('{"a": }', "expected a value, found '}'"),
    ],
)
def test_text_the_scanner_cannot_read(text, message):
    with pytest.raises(JsonSourceError, match=message):
        JsonSource(text)


def test_an_edit_that_gives_the_wrong_document_is_not_made(monkeypatch):
    source = JsonSource(_JSON)
    monkeypatch.setattr(
        JsonSource, "_insert_edits", lambda *args: [(0, len(_JSON), '{"x": 1}')]
    )

    with pytest.raises(JsonSourceError, match="did not give the expected document"):
        source.add("/register/-", {"name": "irq"})
    assert source.text == _JSON
