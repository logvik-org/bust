"""A register map being edited: its data, the text of its file, and the checks.

RegisterMapDocument is the editing API under the console editor, and the one a
web editor would call. A change is a list of JSON Patch operations (RFC 6902)
such as ``{"op": "replace", "path": "/module/register/3/sw", "value": "ro"}``.
Every change goes through Bus and Module, as the command line does, so the
document never holds a register map bust would reject.
"""

import copy
import json
import logging
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple

from bust.core.bus import Bus
from bust.core.legacy_schema import migrate_register_map, register_access_defaults
from bust.core.module import Module
from bust.editing.json_source import (
    JsonSource,
    JsonSourceError,
    apply_to_data,
    join_pointer,
    split_pointer,
)
from bust.settings import Settings
from bust.utils.json_utils import json_parser
from bust.validation.schema_check import check_register_map

Operation = Dict[str, Any]


class EditRejected(ValueError):
    """Raised for a change that would give a register map bust rejects.

    The message has one line for each problem.
    """


class FileChanged(RuntimeError):
    """Raised when the file changed on disk after the document was read."""


class RegisterMapDocument:
    """A register map, changed by JSON Patch operations and saved in place.

    Saving changes only the text of the values that changed, through
    JsonSource. If JsonSource reads the file differently from json_parser, the
    document still works, but saving rewrites the whole file, and
    `keeps_formatting` is False.

    """

    def __init__(self, text: str, data: Any, saved_text: Optional[str]) -> None:
        """Create a document. Use `open` or `new` instead.

        Args:
            text: The text the document starts from.
            data: The register map `text` parses to.
            saved_text: The text of the file on disk, None for a new file.
        """
        self._data = data
        self._saved_text = saved_text
        self._saved_data = copy.deepcopy(data) if saved_text is not None else None
        self._source: Optional[JsonSource]
        try:
            self._source = JsonSource(text)
        except JsonSourceError:
            self._source = None
        if self._source is not None and not _same(self._source.value, data):
            self._source = None
        self._module: Optional[Module] = None

    @classmethod
    def open(cls, path: str) -> "RegisterMapDocument":
        """Read a register map file without checking it. Call `check` next."""
        # newline="" keeps CRLF line endings, so saving does not change them.
        with open(path, encoding="utf-8", newline="") as fp:
            text = fp.read()
        return cls(text, json_parser(path), saved_text=text)

    @classmethod
    def new(cls, bus: Dict, module: Dict) -> "RegisterMapDocument":
        """Start a register map with no registers.

        Raises:
            EditRejected: If bust rejects the bus or module settings.
        """
        data = {"bus": bus, "module": {**module, "register": []}}
        document = cls(json.dumps(data, indent=4) + "\n", data, saved_text=None)
        document.check()
        return document

    @property
    def module(self) -> Module:
        """The Module the current data builds.

        Raises:
            RuntimeError: Before the first `check` or `apply`.
        """
        if self._module is None:
            raise RuntimeError("The register map has not been checked yet")
        return self._module

    @property
    def data(self) -> Any:
        """A copy of the register map as Python data."""
        return copy.deepcopy(self._data)

    @property
    def text(self) -> str:
        """The text that saving writes."""
        if self._source is not None:
            return self._source.text
        return json.dumps(self._data, indent=4, ensure_ascii=False) + "\n"

    @property
    def keeps_formatting(self) -> bool:
        """False if saving rewrites the whole file."""
        return self._source is not None

    @property
    def is_modified(self) -> bool:
        """True if the data differs from the file, or there is no file yet."""
        return self._saved_data is None or not _same(self._data, self._saved_data)

    def check(self) -> List[str]:
        """Check the current data as the command line would.

        Returns:
            The warnings bust gives about it.

        Raises:
            EditRejected: With bust's message, if bust rejects the data.
        """
        self._module, warnings = _build_module(self._data)
        return warnings

    def apply(self, operations: List[Operation]) -> List[str]:
        """Make all the operations, or none of them if bust rejects the result.

        An operation that sets a value equal to the current one is skipped, so
        it does not change how the value is written.

        Returns:
            The warnings bust gives about the result.

        Raises:
            EditRejected: With bust's message. The document stays as it was.
        """
        source = JsonSource(self._source.text) if self._source is not None else None
        data = self._patched(operations, source)
        self._module, warnings = _build_module(data)
        self._data = data
        self._source = source
        return warnings

    def check_operations(self, operations: List[Operation]) -> List[str]:
        """Check the operations as `apply` does, without making them.

        Returns:
            The warnings bust would give about the result.

        Raises:
            EditRejected: With bust's message.
        """
        _, warnings = _build_module(self._patched(operations, None))
        return warnings

    def _patched(
        self, operations: List[Operation], source: Optional[JsonSource]
    ) -> Any:
        """A copy of the data with the operations made, also on `source`."""
        data = copy.deepcopy(self._data)
        try:
            for operation in operations:
                op = operation["op"]
                path = operation["path"]
                value = operation.get("value")
                if op != "remove" and _holds(data, path, value):
                    continue
                # `before` is not in RFC 6902, which tells readers to ignore
                # members they do not know. It places a new key in an object.
                before = operation.get("before")
                apply_to_data(data, op, path, copy.deepcopy(value), before)
                if source is None:
                    continue
                if op == "add":
                    source.add(path, value, before)
                elif op == "remove":
                    source.remove(path)
                else:
                    source.replace(path, value)
        except (KeyError, JsonSourceError) as error:
            raise EditRejected(_message(error)) from error
        return data

    def next_free_address(self) -> int:
        """The address bust would give a register added without one."""
        module, _ = _build_module(self._data)
        return module.get_next_address()

    def legacy_conversion(self) -> Tuple[List[str], List[Operation]]:
        """The changes that turn a bust 0.14 register map into the 1.0 form.

        Each register's `mode` becomes the access keys it stands for, in its
        place. `bust --migrate` makes these changes.

        Returns:
            A description of each change, and the operations that make them.
            Both are empty for a register map in the 1.0 form.

        Raises:
            EditRejected: If the register map uses 0.14 timing bust 1.0 cannot
                generate.
        """
        migrated = self.data
        try:
            changes = migrate_register_map(migrated)
        except Exception as error:
            raise EditRejected(_message(error)) from error
        operations = diff_operations(self._data, migrated)
        for index, register in enumerate(migrated["module"]["register"]):
            if "mode" not in register:
                continue
            path = join_pointer("module", "register", index)
            access = register_access_defaults({"mode": register["mode"]})
            operations += [
                {
                    "op": "add",
                    "path": path + join_pointer(key),
                    "value": value,
                    "before": "mode",
                }
                for key, value in access.items()
            ]
            operations.append({"op": "remove", "path": path + "/mode"})
            keys = ", ".join(f"{key} {json.dumps(v)}" for key, v in access.items())
            changes.append(f"{register['name']}: mode {register['mode']} is now {keys}")
        return changes, operations

    def save(self, path: str) -> bool:
        """Write the register map to `path` if it changed.

        Returns:
            True if the file was written.

        Raises:
            FileChanged: If the file changed on disk since it was read.
            FileExistsError: If a new register map would replace a file.
        """
        if not self.is_modified:
            return False
        text = self.text
        if self._saved_text is None:
            mode = "x"
        else:
            mode = "w"
            with open(path, encoding="utf-8", newline="") as fp:
                if fp.read() != self._saved_text:
                    raise FileChanged(
                        f"{path} changed after the editor read it, so it was "
                        "not saved"
                    )
        with open(path, mode, encoding="utf-8", newline="") as fp:
            fp.write(text)
        self._saved_text = text
        self._saved_data = copy.deepcopy(self._data)
        return True


def diff_operations(old: Any, new: Any, path: str = "") -> List[Operation]:
    """The JSON Patch operations that turn `old` into `new`.

    Lists of equal length are compared element by element, other lists are
    replaced whole.
    """
    if isinstance(old, dict) and isinstance(new, dict):
        operations = [
            {"op": "remove", "path": path + join_pointer(key)}
            for key in old
            if key not in new
        ]
        for key, value in new.items():
            child = path + join_pointer(key)
            if key in old:
                operations += diff_operations(old[key], value, child)
            else:
                operations.append({"op": "add", "path": child, "value": value})
        return operations
    if isinstance(old, list) and isinstance(new, list) and len(old) == len(new):
        return [
            operation
            for index, (a, b) in enumerate(zip(old, new))
            for operation in diff_operations(a, b, path + join_pointer(index))
        ]
    if _same(old, new):
        return []
    return [{"op": "replace", "path": path, "value": new}]


def _same(a: Any, b: Any) -> bool:
    """Equal as JSON, where true is not 1."""
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def _holds(data: Any, path: str, value: Any) -> bool:
    """True if `path` exists in `data` and holds `value`."""
    current = data
    for token in split_pointer(path):
        if isinstance(current, dict) and token in current:
            current = current[token]
        elif (
            isinstance(current, list) and token.isdigit() and int(token) < len(current)
        ):
            current = current[int(token)]
        else:
            return False
    return _same(current, value)


def _message(error: Exception) -> str:
    # str() of a KeyError quotes its message.
    if isinstance(error, KeyError) and error.args:
        return f"Missing key: {error.args[0]}"
    return str(error) or type(error).__name__


class _WarningList(logging.Handler):
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: List[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@contextmanager
def _captured_warnings() -> Iterator[List[str]]:
    """Collect bust's warnings instead of printing them."""
    logger = logging.getLogger("bust")
    handler = _WarningList()
    propagate = logger.propagate
    logger.addHandler(handler)
    logger.propagate = False
    try:
        yield handler.messages
    finally:
        logger.removeHandler(handler)
        logger.propagate = propagate


def _build_module(data: Any) -> Tuple[Module, List[str]]:
    # The schema check first, as on the command line, so that the messages are
    # the same and list every problem the schema finds.
    report = check_register_map(data)
    if report.errors:
        raise EditRejected("\n".join(str(problem) for problem in report.errors))
    with _captured_warnings() as warnings:
        warnings.extend(str(problem) for problem in report.warnings)
        try:
            settings = Settings(None, data.get("settings"))
            module = Module(data["module"], Bus(data["bus"]), settings)
        # Anything Bus or Module raises means bust rejects the register map.
        except Exception as error:
            raise EditRejected(_message(error)) from error
    return module, warnings
