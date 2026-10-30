"""The messages between a register map editor UI and bust.

The editor in editor-ui/ talks to bust in JSON-RPC 2.0 messages, the same in
every host: cloudbust passes them to bust in Pyodide, an editor on the desktop
to ``python -m bust.editing.bridge`` over stdin and stdout, one message per
line.

Methods:
    schema: The JSON Schema of a register map.
    open {text}: Start editing the register map in `text`.
    new {bus, module}: Start a register map with no registers.
    apply {operations}: Make a change, given as JSON Patch operations.
    undo, redo: Step back or forward through the changes.

Every method but schema returns a state. An accepted state holds the register
map's data and text, bust's warnings, each register and field as bust reads
it (address, bits, access, reset, and the bit segments of the documentation), the address a new register would get, and whether undo and redo can step. A
rejected state holds bust's problems, and the register map stays as it was.
Each problem has the path to the value it is about, as a list of keys and
indexes, and the line for problems in the text given to open.
"""

import json
import sys
from typing import Any, Callable, Dict, List, Optional, TextIO

from bust.editing.document import EditRejected, RegisterMapDocument
from bust.exceptions import FormatError
from bust.generators.register_layout import access_text, bit_segments, reset_text
from bust.schema import register_map_schema
from bust.validation.schema_check import Problem, check_register_map

State = Dict[str, Any]

_TEXT_NAME = "register map"

# The JSON-RPC 2.0 error codes.
_PARSE_ERROR = -32700
_INVALID_REQUEST = -32600
_METHOD_NOT_FOUND = -32601
_INVALID_PARAMS = -32602
# In the range JSON-RPC leaves to the server.
_NO_DOCUMENT = -32000


class NoDocument(RuntimeError):
    """Raised for a change before open or new."""


class EditorBridge:
    """One register map being edited, behind JSON-RPC messages."""

    def __init__(self) -> None:
        self._document: Optional[RegisterMapDocument] = None
        self._warnings: List[str] = []
        self._undo: List[RegisterMapDocument] = []
        self._redo: List[RegisterMapDocument] = []
        self._methods: Dict[str, Callable[..., Any]] = {
            "schema": register_map_schema,
            "open": self.open,
            "new": self.new,
            "apply": self.apply,
            "undo": self.undo,
            "redo": self.redo,
        }

    def handle(self, message: str) -> str:
        """The JSON-RPC response to one JSON-RPC request."""
        try:
            request = json.loads(message)
        except ValueError as error:
            return _error_response(None, _PARSE_ERROR, str(error))
        if not isinstance(request, dict) or not isinstance(request.get("method"), str):
            return _error_response(None, _INVALID_REQUEST, "Not a JSON-RPC request")
        request_id = request.get("id")
        method = self._methods.get(request["method"])
        if method is None:
            return _error_response(
                request_id, _METHOD_NOT_FOUND, f"No method {request['method']}"
            )
        params = request.get("params", {})
        if not isinstance(params, dict):
            return _error_response(
                request_id, _INVALID_PARAMS, "params must be an object"
            )
        try:
            result = method(**params)
        except TypeError as error:
            return _error_response(request_id, _INVALID_PARAMS, str(error))
        except NoDocument as error:
            return _error_response(request_id, _NO_DOCUMENT, str(error))
        return json.dumps({"jsonrpc": "2.0", "id": request_id, "result": result})

    def open(self, text: str) -> State:
        try:
            document = RegisterMapDocument.from_text(text, _TEXT_NAME)
        except FormatError as error:
            return _rejected([_syntax_problem(str(error))])
        # Checked here first, with the text, so that each problem has its line.
        report = check_register_map(document.data, text)
        if report.errors:
            return _rejected(report.errors)
        return self._start(document)

    def new(self, bus: Dict[str, Any], module: Dict[str, Any]) -> State:
        try:
            document = RegisterMapDocument.new(bus, module)
        except EditRejected as error:
            return _rejected(error.problems)
        return self._start(document)

    def apply(self, operations: List[Dict[str, Any]]) -> State:
        document = self._require_document()
        before = RegisterMapDocument.from_text(document.text, _TEXT_NAME)
        try:
            self._warnings = document.apply(operations)
        except EditRejected as error:
            return _rejected(error.problems)
        if document.text != before.text:
            self._undo.append(before)
            self._redo.clear()
        return self._state()

    def undo(self) -> State:
        return self._step(self._undo, self._redo)

    def redo(self) -> State:
        return self._step(self._redo, self._undo)

    def _start(self, document: RegisterMapDocument) -> State:
        try:
            self._warnings = document.check()
        except EditRejected as error:
            return _rejected(error.problems)
        self._document = document
        self._undo.clear()
        self._redo.clear()
        return self._state()

    def _step(
        self, source: List[RegisterMapDocument], target: List[RegisterMapDocument]
    ) -> State:
        if source:
            target.append(self._require_document())
            self._document = source.pop()
            self._warnings = self._document.check()
        return self._state()

    def _require_document(self) -> RegisterMapDocument:
        if self._document is None:
            raise NoDocument("Call open or new first")
        return self._document

    def _state(self) -> State:
        document = self._require_document()
        return {
            "accepted": True,
            "data": document.data,
            "text": document.text,
            "warnings": self._warnings,
            "layout": _layout(document),
            "nextAddress": document.next_free_address(),
            "canUndo": bool(self._undo),
            "canRedo": bool(self._redo),
        }


def _layout(document: RegisterMapDocument) -> Dict[str, Any]:
    """How bust reads each register and field, by name: the addresses and bits
    it chose for those that give none, and the access and reset values with
    the defaults filled in, written as the documentation writes them."""
    return {
        register.name: {
            "address": register.address,
            "width": register.width,
            "type": register.type.value,
            "access": access_text(register),
            "reset": reset_text(register.reset, register.width),
            "segments": [
                {
                    "name": segment.name,
                    "high": segment.high,
                    "low": segment.low,
                    "reset": segment.reset,
                    "isUnused": segment.is_unused,
                }
                for segment in bit_segments(register)
            ],
            "fields": {
                field.name: {
                    "low": field.pos_low,
                    "high": field.pos_high,
                    "access": f"{field.sw.value.upper()}/{field.hw.value.upper()}",
                    "reset": reset_text(field.reset, field.width),
                }
                for field in register.fields
            },
        }
        for register in document.module.registers
    }


def _rejected(problems: List[Problem]) -> State:
    return {"accepted": False, "problems": [_problem_json(p) for p in problems]}


def _problem_json(problem: Problem) -> Dict[str, Any]:
    return {
        "path": list(problem.path),
        "location": problem.location,
        "message": problem.message,
        "line": problem.line,
    }


def _syntax_problem(message: str) -> Problem:
    # parse_json_text gives "register map:LINE:COLUMN: message".
    prefix = f"{_TEXT_NAME}:"
    if message.startswith(prefix):
        line, _, rest = message[len(prefix) :].partition(":")
        _, _, text = rest.partition(": ")
        if line.isdigit() and text:
            return Problem((), text, int(line))
    return Problem((), message)


def _error_response(request_id: Any, code: int, message: str) -> str:
    return json.dumps(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": code, "message": message},
        }
    )


def serve(stdin: TextIO, stdout: TextIO) -> None:
    """Answer one JSON-RPC request per line until stdin closes."""
    bridge = EditorBridge()
    for line in stdin:
        if line.strip():
            stdout.write(bridge.handle(line) + "\n")
            stdout.flush()


if __name__ == "__main__":
    serve(sys.stdin, sys.stdout)
