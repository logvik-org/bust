"""EditorBridge answers the JSON-RPC messages of the editor UI."""

import io
import json
import os

from bust.editing.bridge import EditorBridge, serve
from bust.schema import register_map_schema

_EXAMPLE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "example", "example_axi.json"
)

_SMALL = """{
  "bus": {"type": "axi", "addr_width": 16, "data_width": 32},
  "module": {
    "name": "m",
    "register": [{"name": "ctrl", "sw": "rw", "hw": "r"}]
  }
}
"""


def _call(bridge, method, request_id=1, **params):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
    response = json.loads(bridge.handle(json.dumps(message)))
    assert response["id"] == request_id
    return response


def _result(bridge, method, **params):
    return _call(bridge, method, **params)["result"]


def test_schema_is_bust_schema():
    assert _result(EditorBridge(), "schema") == register_map_schema()


def test_open_returns_data_text_and_warnings():
    with open(_EXAMPLE, encoding="utf-8") as fp:
        text = fp.read()
    state = _result(EditorBridge(), "open", text=text)
    assert state["accepted"] is True
    assert state["text"] == text
    assert state["data"]["module"]["name"] == "example_axi"
    assert state["canUndo"] is False
    assert state["layout"]["reg1"]["address"] == 4
    assert state["layout"]["reg7"]["fields"]["field1"] == [1, 4]
    assert state["nextAddress"] == 56


def test_open_gives_syntax_errors_their_line():
    state = _result(EditorBridge(), "open", text='{\n  "bus": ,\n}')
    assert state["accepted"] is False
    [problem] = state["problems"]
    assert problem["line"] == 2
    assert problem["path"] == []


def test_open_gives_schema_errors_their_path_and_line():
    state = _result(EditorBridge(), "open", text=_SMALL.replace('"rw"', '"rx"'))
    assert state["accepted"] is False
    [problem] = state["problems"]
    assert problem["path"] == ["module", "register", 0, "sw"]
    assert problem["location"] == "module.register[0].sw"
    assert problem["line"] == 5


def test_apply_changes_the_text_and_can_be_undone_and_redone():
    bridge = EditorBridge()
    _result(bridge, "open", text=_SMALL)
    operation = {"op": "replace", "path": "/module/register/0/sw", "value": "ro"}

    state = _result(bridge, "apply", operations=[operation])
    assert state["data"]["module"]["register"][0]["sw"] == "ro"
    assert '"sw": "ro"' in state["text"]
    assert (state["canUndo"], state["canRedo"]) == (True, False)

    state = _result(bridge, "undo")
    assert state["text"] == _SMALL
    assert (state["canUndo"], state["canRedo"]) == (False, True)

    state = _result(bridge, "redo")
    assert state["data"]["module"]["register"][0]["sw"] == "ro"


def test_a_rejected_change_has_problems_and_changes_nothing():
    bridge = EditorBridge()
    _result(bridge, "open", text=_SMALL)
    operation = {"op": "replace", "path": "/module/register/0/sw", "value": "rx"}

    state = _result(bridge, "apply", operations=[operation])
    assert state["accepted"] is False
    assert state["problems"][0]["path"] == ["module", "register", 0, "sw"]
    assert _result(bridge, "undo")["text"] == _SMALL


def test_module_errors_are_rejected_without_a_path():
    bridge = EditorBridge()
    _result(bridge, "open", text=_SMALL)
    operation = {
        "op": "add",
        "path": "/module/register/-",
        "value": {"name": "ctrl", "sw": "rw", "hw": "r"},
    }
    state = _result(bridge, "apply", operations=[operation])
    assert state["accepted"] is False
    assert state["problems"][0]["path"] == []
    assert "ctrl" in state["problems"][0]["message"]


def test_new_starts_an_empty_register_map():
    state = _result(
        EditorBridge(),
        "new",
        bus={"type": "axi", "addr_width": 16, "data_width": 32},
        module={"name": "m"},
    )
    assert state["accepted"] is True
    assert state["data"]["module"]["register"] == []


def test_a_change_before_open_is_an_error():
    response = _call(EditorBridge(), "apply", operations=[])
    assert response["error"]["code"] == -32000


def test_unknown_methods_and_bad_messages_are_errors():
    bridge = EditorBridge()
    assert _call(bridge, "save")["error"]["code"] == -32601
    assert _call(bridge, "open", wrong=1)["error"]["code"] == -32602
    assert json.loads(bridge.handle("not json"))["error"]["code"] == -32700
    assert json.loads(bridge.handle("[]"))["error"]["code"] == -32600


def test_serve_answers_one_line_per_request():
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "open", "params": {"text": _SMALL}},
        {"jsonrpc": "2.0", "id": 2, "method": "undo"},
    ]
    stdin = io.StringIO("".join(json.dumps(r) + "\n" for r in requests))
    stdout = io.StringIO()
    serve(stdin, stdout)
    responses = [json.loads(line) for line in stdout.getvalue().splitlines()]
    assert [r["id"] for r in responses] == [1, 2]
    assert all(r["result"]["accepted"] for r in responses)
