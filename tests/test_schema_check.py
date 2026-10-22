"""bust checks a register map against its JSON Schema and reports every problem
at once, each with its path and line (#234)."""

import copy
import glob
import json
import os

import jsonschema
import pytest

from bust.editing.json_source import JsonSource
from bust.exceptions import FormatError
from bust.schema import register_map_schema
from bust.utils.json_utils import json_parser, parse_json_text
from bust.validation.schema_check import Problem, check_register_map

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_FILES = sorted(
    glob.glob(os.path.join(_REPO_ROOT, "example", "*.json"))
    + glob.glob(os.path.join(_REPO_ROOT, "tests", "data", "**", "*.json"))
)

_REGISTER_MAP = {
    "bus": {"type": "axi", "addr_width": 16, "data_width": 32},
    "module": {
        "name": "m",
        "register": [
            {"name": "ctrl", "sw": "rw"},
            {
                "name": "status",
                "type": "fields",
                "fields": [{"name": "busy", "type": "bit", "hw": "w"}],
            },
        ],
    },
}


def _changed(path, value):
    """The register map with the value at `path` set, or removed for None."""
    register_map = copy.deepcopy(_REGISTER_MAP)
    *parents, last = path
    target = register_map
    for token in parents:
        target = target[token]
    if value is None:
        del target[last]
    else:
        target[last] = value
    return register_map


def _errors(register_map):
    return [str(problem) for problem in check_register_map(register_map).errors]


@pytest.mark.parametrize("path", _FILES, ids=lambda p: os.path.relpath(p, _REPO_ROOT))
def test_files_bust_reads_pass(path):
    assert check_register_map(json_parser(path)).errors == []


def test_every_problem_in_one_run_with_its_line():
    text = """{
  "bus": {"type": "axi", "addr_width": 16, "data_width": 32},
  "module": {
    "name": "m",
    "register": [
      {"name": "a"},
      {"name": "b", "sw": "rx"},
      {"name": "c"},
      {
        "name": "d",
        "address": "1c",
        "type": "fields",
        "fields": [
          {"name": "x", "type": "bit"},
          {"name": "y", "type": "bit", "onwrit": "woclr"}
        ]
      }
    ]
  }
}
"""
    report = check_register_map(parse_json_text(text, "m.json"), text)

    assert [p.in_file("m.json") for p in report.errors] == [
        'm.json:7: module.register[1].sw: "rx" is not one of "rw", "ro", "wo", '
        '"na". Did you mean "rw"?',
        'm.json:11: module.register[3].address: "1c" has hexadecimal digits but '
        'no 0x. Write "0x1c" for a hexadecimal number.',
    ]
    assert [p.in_file("m.json") for p in report.warnings] == [
        "m.json:15: module.register[3].fields[1].onwrit: bust does not know "
        "this key and ignores it. Did you mean 'onwrite'?"
    ]


@pytest.mark.parametrize(
    "path, value, message",
    [
        (("bus", "type"), "pci", 'bus.type: "pci" is not one of "axi", '),
        (("bus", "addr_width"), -4, "bus.addr_width: must not be negative (got -4)"),
        (
            ("bus", "data_width"),
            "32 bits",
            'bus.data_width: must be a whole number such as 16, "0x10" or "0b10000"',
        ),
        (("bus", "data_width"), 32.0, "bus.data_width: must be a whole number"),
        (("bus", "data_width"), True, "bus.data_width: must be a whole number"),
        (("module", "name"), 7, "module.name: must be a string (got 7)"),
        (
            ("module", "byte_addressable"),
            "yes",
            'module.byte_addressable: must be true or false (got "yes")',
        ),
        (("module", "register"), {}, "module.register: must be a list (got {})"),
        (("module", "register", 0, "name"), None, "module.register[0]: missing key"),
        (
            ("module", "register", 0, "we"),
            "false",
            'module.register[0].we: must be true or false (got "false")',
        ),
        (
            ("module", "register", 1, "fields"),
            [],
            "module.register[1].fields: must not be empty",
        ),
        (
            ("module", "register", 1, "fields", 0, "type"),
            "vectr",
            'module.register[1].fields[0].type: "vectr" is not one of "vector", '
            '"bit". Did you mean "vector"?',
        ),
        (
            ("module", "register", 1, "fields", 0, "enums"),
            [{"name": "on"}],
            "module.register[1].fields[0].enums[0]: missing key 'value'",
        ),
        (("module",), None, "missing key 'module'"),
    ],
)
def test_messages(path, value, message):
    errors = _errors(_changed(path, value))

    assert len(errors) == 1
    assert errors[0].startswith(message)


def test_a_file_that_is_not_an_object():
    assert _errors([]) == ["must be an object (got [])"]


def test_unknown_keys_are_warnings():
    report = check_register_map(_changed(("module", "registers"), []))

    assert report.errors == []
    assert [str(problem) for problem in report.warnings] == [
        "module.registers: bust does not know this key and ignores it. Did you "
        "mean 'register'?"
    ]


@pytest.mark.parametrize(
    "path, value",
    [
        (("module", "register", 0, "sw"), "RW"),
        (("module", "register", 0, "type"), "SLV"),
        (("module", "register", 1, "fields", 0, "type"), "sl"),
        (("module", "byte_addressable"), "False"),
        (("module", "register", 0, "mode"), "pulse"),
        (("settings",), {"coverage": True}),
        (("module", "register", 0, "address"), "0X1C"),
        (("module", "register", 0, "we"), False),
    ],
)
def test_forms_bust_reads_are_not_problems(path, value):
    register_map = _changed(path, value)

    report = check_register_map(register_map)

    assert report.errors == report.warnings == []


def test_null_counts_as_false():
    register_map = copy.deepcopy(_REGISTER_MAP)
    register_map["module"]["register"][0]["we"] = None

    assert check_register_map(register_map).errors == []


def test_the_check_does_not_change_the_data():
    register_map = _changed(("module", "register", 0, "sw"), "RW")
    before = copy.deepcopy(register_map)

    check_register_map(register_map)

    assert register_map == before


# Values that the schema rejects. The check must agree with jsonschema about
# each of them, so that bust and editors that read the schema agree.
_CHANGES = [
    (("bus", "type"), "pci"),
    (("bus", "addr_width"), "0x"),
    (("bus", "addr_width"), -1),
    (("bus", "data_width"), "0b12"),
    (("bus", "data_width"), None),
    (("module", "name"), ["m"]),
    (("module", "version"), 1),
    (("module", "byte_addressable"), 1),
    (("module", "register"), "ctrl"),
    (("module", "register", 0), "ctrl"),
    (("module", "register", 0, "name"), None),
    (("module", "register", 0, "hw"), "x"),
    (("module", "register", 0, "onread"), "rclr "),
    (("module", "register", 0, "swmod"), 1),
    (("module", "register", 0, "reset"), "1f"),
    (("module", "register", 1, "fields"), []),
    (("module", "register", 1, "fields"), {}),
    (("module", "register", 1, "fields", 0, "position"), -2),
    (("module", "register", 1, "fields", 0, "enums"), [{"name": 1, "value": 0}]),
    (("module", "register", 1, "fields", 0, "enums"), [{"name": "a", "value": "x"}]),
    (("module", "register", 1, "fields", 0, "type"), None),
]


@pytest.mark.parametrize("path, value", _CHANGES)
def test_agrees_with_jsonschema(path, value):
    register_map = _changed(path, value)
    expected = [
        error
        for error in jsonschema.Draft202012Validator(register_map_schema()).iter_errors(
            register_map
        )
        if error.validator != "additionalProperties"
    ]

    errors = check_register_map(register_map).errors

    assert errors
    assert {tuple(e.absolute_path) for e in expected} == {e.path for e in errors}


def test_agrees_with_jsonschema_on_a_valid_map():
    jsonschema.Draft202012Validator(register_map_schema()).validate(_REGISTER_MAP)
    assert check_register_map(_REGISTER_MAP).errors == []


def test_a_problem_without_a_line():
    problem = Problem(("module", "register", 2, "sw"), "is wrong")

    assert problem.in_file("m.json") == "m.json: module.register[2].sw: is wrong"


def test_lines_for_a_json5_file():
    text = "// A register map\n{\n  bus: {type: 'pci', addr_width: 8, data_width: 32},\n  module: {name: 'm', register: []},\n}\n"

    report = check_register_map(parse_json_text(text, "m.json5"), text)

    assert [problem.line for problem in report.errors] == [3]


def test_json_source_line():
    source = JsonSource('{\n  "a": [\n    1,\n    {"b": 2}\n  ]\n}\n')

    assert source.line("") == 1
    assert source.line("/a") == 2
    assert source.line("/a/1") == 4
    assert source.line("/a/1/b") == 4


@pytest.mark.parametrize(
    "text, message",
    [
        ('{"a": 1 "b": 2}', "m.json:1:9: Expecting ',' delimiter"),
        ('{\n  "a": [1, 2}\n', "m.json:2:13: Expecting ',' delimiter"),
        ("{\n  // a comment\n  a: 1,\n  b: 2 c: 3\n}", "m.json:4:8: Unexpected 'c'"),
        ('{"a": "x\n"}', "m.json:1:9: Unexpected end of line"),
        ("{", "m.json:1:2:"),
        (" \n", "m.json is empty"),
    ],
)
def test_syntax_errors_give_the_place(text, message):
    with pytest.raises(FormatError) as error:
        parse_json_text(text, "m.json")

    assert str(error.value).startswith(message)


def test_json5_still_parses():
    assert parse_json_text("{a: 0x1c, b: [1,],}", "m.json5") == {"a": 28, "b": [1]}


def test_problems_are_json():
    # The message shows the value as it is written in the file.
    errors = _errors(_changed(("module", "register", 0, "sw"), "é"))

    assert errors[0].startswith(f'module.register[0].sw: {json.dumps("é")[0]}é"')
