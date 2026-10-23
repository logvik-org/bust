"""Check a register map against its JSON Schema and report every problem.

bust checks the whole file against the schema in bust.schema before it builds
Bus and Module, so that one run lists every misspelt value, wrong type and
missing key, each with its place in the file. The rules that span keys, such as
two registers at one address, stay in Module, which runs after this check
passes.

The checker covers the parts of JSON Schema that bust.schema uses: type, enum,
pattern, minimum, minItems, required, properties, additionalProperties, items,
anyOf and $ref. A key the schema does not list gives a warning, not an error,
as bust ignores it. The keys and values of bust 0.14 are errors that point to
--migrate.
"""

import copy
import difflib
import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

from bust.editing.json_source import JsonSource, JsonSourceError, join_pointer
from bust.exceptions import FormatError
from bust.schema import NUMBER_FORMS, register_map_schema
from bust.validation.config_validator import parse_number

Path = Tuple[Union[str, int], ...]

_SCHEMA = register_map_schema()

# bust reads these values in any case, as Enum.from_string lowers them.
_CASE_FREE_KEYS = ("type", "sw", "hw", "onread", "onwrite")

_MIGRATE = "Run bust with --migrate to convert the file."

# The keys of bust 0.14 that bust 1.0 does not read, by the object they sit in.
_OLD_KEYS = {
    "top": ("settings",),
    "bus": ("comp_library", "reset"),
    "module": ("git_hash",),
    "register": ("mode", "pulse_cycles", "stall_cycles"),
}

# The bust 0.14 names of the bit and vector types.
_OLD_TYPE_NAMES = {"sl": "bit", "slv": "vector"}

# The JSON Schema keywords the check applies, and the ones it reads past
# because they only describe. tests/test_schema_check.py fails if the schema
# uses any other keyword, so that a new one gets support here first.
CHECKED_KEYWORDS = frozenset(
    [
        "type",
        "enum",
        "pattern",
        "minimum",
        "minItems",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "anyOf",
        "$ref",
    ]
)
ANNOTATION_KEYWORDS = frozenset(["$schema", "$defs", "title", "description", "default"])

_TYPE_NAMES = {
    "string": "a string",
    "integer": "a whole number",
    "boolean": "true or false",
    "array": "a list",
    "object": "an object",
}


@dataclass(frozen=True)
class Problem:
    """One problem in a register map.

    Attributes:
        path: The keys and list indexes that lead to the value.
        message: What is wrong, without the place.
        line: The line in the file, counted from 1, if known.
    """

    path: Path
    message: str
    line: Optional[int] = None

    @property
    def location(self) -> str:
        """The path as module.register[2].sw."""
        text = ""
        for token in self.path:
            text += f"[{token}]" if isinstance(token, int) else f".{token}"
        return text.lstrip(".")

    def __str__(self) -> str:
        if not self.path:
            return self.message
        return f"{self.location}: {self.message}"

    def in_file(self, filename: str) -> str:
        """The problem with the file name and line in front, as compilers give it."""
        place = filename if self.line is None else f"{filename}:{self.line}"
        return f"{place}: {self}"


@dataclass
class SchemaReport:
    """What the schema check found.

    Attributes:
        errors: Problems that stop bust.
        warnings: Keys bust does not know and ignores.
    """

    errors: List[Problem]
    warnings: List[Problem]


def check_register_map(data: Any, text: Optional[str] = None) -> SchemaReport:
    """Check a register map against the schema.

    Args:
        data: The register map as json_parser returns it.
        text: The text of the file, to give each problem its line.

    Returns:
        Every problem the schema finds, in the order of the file.
    """
    copied = copy.deepcopy(data)
    errors = [Problem(path, message) for path, message in _take_old_forms(copied)]
    warnings: List[Problem] = []
    for is_error, path, message in _check(_as_bust_reads(copied), _SCHEMA, ()):
        (errors if is_error else warnings).append(Problem(path, message))
    errors.sort(key=lambda problem: _order(data, problem.path))
    lines = _LineFinder(text)
    return SchemaReport(
        [lines.place(p) for p in errors], [lines.place(p) for p in warnings]
    )


def _take_old_forms(data: Any) -> Iterator[Tuple[Path, str]]:
    """Yield a problem for each bust 0.14 key and value, and take it out of
    `data`, so that the schema check does not report it again."""
    if not isinstance(data, dict):
        return
    yield from _take_old_keys(data, "top", ())
    if isinstance(data.get("bus"), dict):
        yield from _take_old_keys(data["bus"], "bus", ("bus",))
    module = data.get("module")
    if not isinstance(module, dict):
        return
    yield from _take_old_keys(module, "module", ("module",))
    value = module.get("byte_addressable")
    if value in ("True", "False"):
        del module["byte_addressable"]
        yield ("module", "byte_addressable"), (
            f'"{value}" is the bust 0.14 form of {value.lower()}. {_MIGRATE}'
        )
    registers = module.get("register")
    for index, register in enumerate(registers if isinstance(registers, list) else []):
        if not isinstance(register, dict):
            continue
        path: Path = ("module", "register", index)
        yield from _take_old_keys(register, "register", path)
        yield from _take_old_type(register, path)
        fields = register.get("fields")
        for number, field in enumerate(fields if isinstance(fields, list) else []):
            if isinstance(field, dict):
                yield from _take_old_type(field, path + ("fields", number))


def _take_old_keys(
    config: Dict[str, Any], kind: str, path: Path
) -> Iterator[Tuple[Path, str]]:
    for key in _OLD_KEYS[kind]:
        if key in config:
            del config[key]
            yield path + (
                key,
            ), f"a bust 0.14 key, which bust no longer reads. {_MIGRATE}"


def _take_old_type(config: Dict[str, Any], path: Path) -> Iterator[Tuple[Path, str]]:
    value = config.get("type")
    if isinstance(value, str) and value.lower() in _OLD_TYPE_NAMES:
        new = _OLD_TYPE_NAMES[value.lower()]
        config["type"] = new
        yield path + ("type",), (
            f'"{value}" is the bust 0.14 name of "{new}". {_MIGRATE}'
        )


def _order(data: Any, path: Path) -> Tuple[Any, ...]:
    """A key that sorts problems in the order of their place in the file."""
    order: List[Any] = []
    current = data
    for token in path:
        if isinstance(current, list) and isinstance(token, int):
            order.append(token)
            current = current[token] if token < len(current) else None
        elif isinstance(current, dict):
            keys = list(current)
            order.append(keys.index(token) if token in keys else len(keys))
            current = current.get(token)
        else:
            order.append(0)
            current = None
    return tuple(order)


def _as_bust_reads(data: Any) -> Any:
    """A copy of the data with the forms bust reads but the schema does not
    describe, such as upper-case values, turned into the form it describes."""
    data = copy.deepcopy(data)
    module = data.get("module") if isinstance(data, dict) else None
    if not isinstance(module, dict):
        return data
    registers = module.get("register")
    for register in registers if isinstance(registers, list) else []:
        if not isinstance(register, dict):
            continue
        _lower_case_keys(register)
        fields = register.get("fields")
        for field in fields if isinstance(fields, list) else []:
            if isinstance(field, dict):
                _lower_case_keys(field)
    return data


def _lower_case_keys(config: Dict[str, Any]) -> None:
    for key in _CASE_FREE_KEYS:
        if isinstance(config.get(key), str):
            config[key] = config[key].lower()


def _check(
    value: Any, schema: Dict[str, Any], path: Path
) -> Iterator[Tuple[bool, Path, str]]:
    """Yield (is_error, path, message) for each problem, depth first."""
    if "$ref" in schema:
        schema = _resolve(schema["$ref"])
    if "anyOf" in schema:
        if not any(_is_valid(value, branch) for branch in schema["anyOf"]):
            yield True, path, _any_of_message(value, schema)
        return
    if "type" in schema and not _has_type(value, schema["type"]):
        yield True, path, _type_message(value, schema["type"])
        return
    if "enum" in schema and value not in schema["enum"]:
        yield True, path, _enum_message(value, schema["enum"])
    if "pattern" in schema and not re.search(schema["pattern"], value):
        yield True, path, _pattern_message(value, schema)
    if "minimum" in schema and value < schema["minimum"]:
        yield True, path, f"must be at least {schema['minimum']} (got {value})"
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            yield True, path, "must not be empty"
        for index, item in enumerate(value):
            yield from _check(item, schema.get("items", {}), path + (index,))
    if isinstance(value, dict):
        yield from _check_object(value, schema, path)


def _check_object(
    value: Dict[str, Any], schema: Dict[str, Any], path: Path
) -> Iterator[Tuple[bool, Path, str]]:
    properties = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in value:
            yield True, path, f"missing key '{key}'"
    for key, item in value.items():
        if key in properties:
            yield from _check(item, properties[key], path + (key,))
        elif schema.get("additionalProperties", True) is False:
            message = "bust does not know this key and ignores it"
            hint = _did_you_mean(key, properties, "'{}'", cutoff=0.75)
            yield False, path + (key,), message + hint


def _is_valid(value: Any, schema: Dict[str, Any]) -> bool:
    return not any(is_error for is_error, _, _ in _check(value, schema, ()))


def _resolve(ref: str) -> Dict[str, Any]:
    if not ref.startswith("#/$defs/"):
        raise ValueError(f"bust's schema check cannot resolve {ref}")
    definition: Dict[str, Any] = _SCHEMA["$defs"][ref[len("#/$defs/") :]]
    return definition


def _has_type(value: Any, expected: Union[str, List[str]]) -> bool:
    types = [expected] if isinstance(expected, str) else expected
    return any(_is_type(value, t) for t in types)


def _is_type(value: Any, name: str) -> bool:
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "null":
        return value is None
    python_type = {"string": str, "boolean": bool, "array": list, "object": dict}
    return isinstance(value, python_type[name])


def _shown(value: Any) -> str:
    """The value as JSON, shortened if long."""
    text = json.dumps(value, ensure_ascii=False)
    return text if len(text) <= 40 else text[:37] + "..."


def _type_message(value: Any, expected: Union[str, List[str]]) -> str:
    types = [expected] if isinstance(expected, str) else expected
    # null counts as false for the flags, which the message need not say.
    names = [_TYPE_NAMES[t] for t in types if t != "null"]
    return f"must be {' or '.join(names)} (got {_shown(value)})"


def _enum_message(value: Any, allowed: List[Any]) -> str:
    choices = ", ".join(_shown(v) for v in allowed)
    message = f"{_shown(value)} is not one of {choices}"
    if isinstance(value, str):
        message += _did_you_mean(value.lower(), allowed, '"{}"', cutoff=0.5)
    return message


def _pattern_message(value: str, schema: Dict[str, Any]) -> str:
    description = schema.get("description")
    message = f"{_shown(value)} is not valid here"
    return f"{message}. {description}" if description else message


def _any_of_message(value: Any, schema: Dict[str, Any]) -> str:
    if schema["anyOf"] == NUMBER_FORMS:
        # parse_number has the wording, and the hint for a missing 0x.
        try:
            parse_number(value, "The value")
        except FormatError as error:
            return _lower_first(str(error).replace("The value ", "", 1))
    return f"{_shown(value)} is not valid here"


def _lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def _did_you_mean(word: str, choices: Any, quoted: str, cutoff: float) -> str:
    matches = difflib.get_close_matches(
        word, [str(c) for c in choices], n=1, cutoff=cutoff
    )
    return f". Did you mean {quoted.format(matches[0])}?" if matches else ""


class _LineFinder:
    """Finds the line of a value in the text of the file."""

    def __init__(self, text: Optional[str]) -> None:
        self._source: Optional[JsonSource] = None
        if text is not None:
            try:
                self._source = JsonSource(text)
            except JsonSourceError:
                pass

    def place(self, problem: Problem) -> Problem:
        if self._source is None:
            return problem
        try:
            line = self._source.line(join_pointer(*problem.path))
        except JsonSourceError:
            return problem
        return Problem(problem.path, problem.message, line)
