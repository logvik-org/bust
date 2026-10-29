"""The JSON Schema (draft 2020-12) of a bust register map.

The schema lists each key with its allowed values, its default and a short
description. Editors build their prompts and forms from it, so the allowed
values come from the enums in bust.core.enums and exist in one place. Rules
that span keys, such as an onread on a field software cannot read, are not in
the schema. Module checks those.
"""

import copy
from typing import Any, Dict, List

from bust.core.bus import Bus
from bust.core.module import VERSION_PATTERN
from bust.core.enums import (
    FieldType,
    HwAccess,
    OnRead,
    OnWrite,
    RegisterType,
    SwAccess,
)

# The docs build writes the schema to this address, and Read the Docs rebuilds
# stable on each release. A register map points to it with a "$schema" key.
SCHEMA_URL = "https://bust.readthedocs.io/en/stable/register-map.schema.json"

# The forms parse_number reads. JSON5 0x1c parses to an integer, JSON "0x1c"
# to a string.
_NUMBER_PATTERN = r"^(0[xX][0-9a-fA-F]+|0[bB][01]+|[0-9]+)$"

# The anyOf of every number, which the schema check recognises to word its
# message.
NUMBER_FORMS: List[Dict[str, Any]] = [
    {"type": "integer", "minimum": 0},
    {"type": "string", "pattern": _NUMBER_PATTERN},
]


def _number(description: str, **extra: Any) -> Dict[str, Any]:
    return {
        "description": description,
        "anyOf": copy.deepcopy(NUMBER_FORMS),
        **extra,
    }


def _choice(description: str, values: List[str], **extra: Any) -> Dict[str, Any]:
    return {"description": description, "type": "string", "enum": values, **extra}


def _flag(description: str) -> Dict[str, Any]:
    # bust reads null as false.
    return {"description": description, "type": ["boolean", "null"], "default": False}


def _string(description: str, **extra: Any) -> Dict[str, Any]:
    return {"description": description, "type": "string", **extra}


_ACCESS_KEYS: Dict[str, Dict[str, Any]] = {
    "sw": _choice(
        "What software can do: read and write, read only, write only, or nothing.",
        SwAccess.valid_values(),
        default=SwAccess.RW.value,
    ),
    "hw": _choice(
        "What hardware can do: read the value, write it, both, or nothing.",
        HwAccess.valid_values(),
        default=HwAccess.R.value,
    ),
    "onread": _choice(
        "What a software read does to the value afterwards: clear or set it.",
        OnRead.valid_values(),
    ),
    "onwrite": _choice(
        "How a software write changes the value, instead of storing the data.",
        OnWrite.valid_values(),
    ),
    "singlepulse": _flag(
        "A written value reaches hardware for one cycle, then the value "
        "returns to its reset value."
    ),
    "we": _flag("Hardware writes the value only in cycles where we is '1'."),
    "wel": _flag("Hardware writes the value only in cycles where wel is '0'."),
    "hwset": _flag("Hardware sets every bit with a set input."),
    "hwclr": _flag("Hardware clears every bit with a clear input."),
    "swmod": _flag("A strobe to hardware after each software write."),
    "swacc": _flag("A strobe to hardware after each software read or write."),
}

_ENUM_VALUE: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "value"],
    "additionalProperties": False,
    "properties": {
        "name": _string("The name of the value, a VHDL identifier."),
        "value": _number("The encoding of the value."),
    },
}

_FIELD: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "type"],
    "additionalProperties": False,
    "properties": {
        "name": _string("Field name, a VHDL identifier."),
        "type": _choice(
            "bit for a std_logic, vector for a std_logic_vector.",
            FieldType.valid_values(),
        ),
        "width": _number("Width of a vector field.", default=1),
        "position": _number("Lowest bit of the field. Default: the next free bit."),
        "reset": _number("Reset value of the field.", default=0),
        "description": _string("Shown in the documentation.", default=""),
        "enums": {
            "description": "Named values of the field.",
            "type": "array",
            "items": {"$ref": "#/$defs/enum_value"},
        },
        **_ACCESS_KEYS,
    },
}

_REGISTER: Dict[str, Any] = {
    "type": "object",
    "required": ["name"],
    "additionalProperties": False,
    "properties": {
        "name": _string("Register name, a VHDL identifier."),
        "description": _string("Shown in the documentation.", default=""),
        "address": _number(
            "Register offset from the module's base address. Default: the "
            "lowest free address."
        ),
        "type": _choice(
            "default for data_width bits, vector for width bits, bit for one "
            "bit, fields for a register made of fields, hash and version for "
            "read-only registers that hold the register map hash and version.",
            RegisterType.valid_values(),
            default=RegisterType.DEFAULT.value,
        ),
        "width": _number("Width of a vector register. Default: data_width."),
        "reset": _number("Reset value of a register without fields.", default=0),
        "fields": {
            "description": "The fields of a fields register.",
            "type": "array",
            "minItems": 1,
            "items": {"$ref": "#/$defs/field"},
        },
        **_ACCESS_KEYS,
    },
}

_MODULE: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "register"],
    "additionalProperties": False,
    "properties": {
        "name": _string("Module name, a VHDL identifier."),
        "description": _string("Shown in the documentation.", default=""),
        "version": _string(
            "The version of the register map, which every generated file "
            'carries. Printable ASCII other than ", \\, ; and =. A version '
            "register needs MAJOR.MINOR or MAJOR.MINOR.PATCH.",
            default="",
            pattern=f"^{VERSION_PATTERN.pattern}$",
        ),
        "byte_addressable": {
            "description": "true if an address counts bytes, false if it counts "
            "data words. Default: from the bus.",
            "type": "boolean",
        },
        "reserved_fields": {
            "description": "true to show the bits that no field covers as "
            "reserved fields in the documentation.",
            "type": "boolean",
            "default": False,
        },
        "register": {
            "description": "The registers.",
            "type": "array",
            "items": {"$ref": "#/$defs/register"},
        },
    },
}

_BUS: Dict[str, Any] = {
    "type": "object",
    "required": ["type", "addr_width", "data_width"],
    "additionalProperties": False,
    "properties": {
        "type": _choice("The bus protocol.", Bus.supported_bus),
        "addr_width": _number("Width of the bus address in bits."),
        "data_width": _number("Width of the bus data in bits, whole bytes."),
    },
}


def register_map_schema() -> Dict[str, Any]:
    """The JSON Schema of a register map file."""
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": SCHEMA_URL,
        "title": "bust register map",
        "type": "object",
        "required": ["bus", "module"],
        "additionalProperties": False,
        "properties": {
            "$schema": _string(
                "The address of this schema, which lets an editor check the "
                "file and complete keys. bust ignores it."
            ),
            "bus": {"$ref": "#/$defs/bus"},
            "module": {"$ref": "#/$defs/module"},
        },
        "$defs": {
            "bus": _BUS,
            "module": _MODULE,
            "register": _REGISTER,
            "field": _FIELD,
            "enum_value": _ENUM_VALUE,
        },
    }
    return copy.deepcopy(schema)
