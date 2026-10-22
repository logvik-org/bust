"""The JSON Schema of the register map describes the keys bust reads."""

import glob
import os

import jsonschema
import pytest

from bust.core.bus import BUS_KEYS
from bust.core.field import FIELD_KEYS
from bust.core.module import MODULE_KEYS
from bust.core.register import REGISTER_KEYS
from bust.schema import register_map_schema
from bust.utils.json_utils import json_parser

_REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
_EXAMPLES = sorted(glob.glob(os.path.join(_REPO_ROOT, "example", "*.json")))

_REGISTER_MAP = {
    "bus": {"type": "axi", "addr_width": 16, "data_width": 32},
    "module": {
        "name": "m",
        "register": [
            {
                "name": "ctrl",
                "address": "0x0",
                "sw": "rw",
                "type": "fields",
                "fields": [{"name": "mode", "type": "vector", "width": 2}],
            }
        ],
    },
}


def _validator():
    return jsonschema.Draft202012Validator(register_map_schema())


def test_the_schema_is_valid():
    jsonschema.Draft202012Validator.check_schema(register_map_schema())


@pytest.mark.parametrize(
    "path", _EXAMPLES, ids=lambda p: os.path.relpath(p, _REPO_ROOT)
)
def test_every_example_matches(path):
    _validator().validate(json_parser(path))


@pytest.mark.parametrize(
    "definition, keys",
    [
        ("bus", set(BUS_KEYS)),
        ("module", set(MODULE_KEYS)),
        ("register", REGISTER_KEYS),
        ("field", FIELD_KEYS),
    ],
)
def test_the_schema_has_the_keys_bust_reads(definition, keys):
    assert set(register_map_schema()["$defs"][definition]["properties"]) == keys


def test_numbers_in_both_forms():
    register = _REGISTER_MAP["module"]["register"][0]
    for address in (28, "28", "0x1c", "0X1C", "0b11100"):
        _validator().validate(
            {
                **_REGISTER_MAP,
                "module": {"name": "m", "register": [{**register, "address": address}]},
            }
        )


@pytest.mark.parametrize(
    "change, message",
    [
        ({"sw": "rx"}, "'rx' is not one of"),
        ({"address": "1c"}, "'1c' is not valid"),
        ({"address": -4}, "-4 is not valid"),
        ({"we": "false"}, "'false' is not of type"),
        ({"onwrit": "woclr"}, "'onwrit' was unexpected"),
    ],
)
def test_what_the_schema_rejects(change, message):
    register = {**_REGISTER_MAP["module"]["register"][0], **change}
    register_map = {**_REGISTER_MAP, "module": {"name": "m", "register": [register]}}

    with pytest.raises(jsonschema.ValidationError, match=message):
        _validator().validate(register_map)


def test_the_schema_is_a_copy():
    register_map_schema()["$defs"]["bus"]["properties"].clear()

    assert register_map_schema()["$defs"]["bus"]["properties"]
