"""Edit the text of a JSON or JSON5 file without reformatting it.

The json5 package parses register maps. JsonSource only finds where each value
sits in the text, so that an edit replaces, adds or removes the text of one
value and leaves comments, key order, number forms and whitespace alone.

Values are addressed by JSON Pointer (RFC 6901), such as
``/module/register/3/reset``. New values are written as plain JSON, which is
valid in both JSON and JSON5 files.
"""

import copy
import json
import re
from dataclasses import dataclass
from typing import Any, List, Optional, Tuple

import json5

_WHITESPACE = " \t\n\r\v\f ﻿  "
_WORD_END = set("{}[],:\"'/" + _WHITESPACE)
_ARRAY_INDEX = re.compile(r"0|[1-9][0-9]*")
_IDENTIFIER = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")

# (start, end, replacement) in the text before any of the edits.
_Edit = Tuple[int, int, str]


class JsonSourceError(ValueError):
    """Raised for text the scanner cannot read, or a path that is not there."""


@dataclass
class _Node:
    start: int
    end: int
    # None for a string, number or literal.
    members: Optional[List["_Member"]] = None
    is_object: bool = False


@dataclass
class _Member:
    key: Optional[str]
    # Where the key starts, or the value for a list element.
    start: int
    value: _Node
    comma: Optional[int]


class _Scanner:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def parse(self) -> _Node:
        self._skip()
        node = self._value()
        self._skip()
        if self.pos != len(self.text):
            raise self._error("text after the end of the document")
        return node

    def _error(self, problem: str) -> JsonSourceError:
        line = self.text.count("\n", 0, self.pos) + 1
        return JsonSourceError(f"Line {line}: {problem}")

    def _peek(self) -> str:
        return self.text[self.pos : self.pos + 1]

    def _skip(self) -> None:
        text = self.text
        while self.pos < len(text):
            if text[self.pos] in _WHITESPACE:
                self.pos += 1
            elif text.startswith("//", self.pos):
                end = text.find("\n", self.pos)
                self.pos = len(text) if end < 0 else end
            elif text.startswith("/*", self.pos):
                end = text.find("*/", self.pos + 2)
                if end < 0:
                    raise self._error("unterminated comment")
                self.pos = end + 2
            else:
                return

    def _value(self) -> _Node:
        char = self._peek()
        if char in ("{", "["):
            return self._container(char == "{")
        start = self.pos
        if char in ('"', "'"):
            self._string()
        else:
            self._word()
        return _Node(start, self.pos)

    def _string(self) -> None:
        text = self.text
        quote = text[self.pos]
        i = self.pos + 1
        while i < len(text) and text[i] != "\n":
            if text[i] == "\\":
                i += 2
            elif text[i] == quote:
                self.pos = i + 1
                return
            else:
                i += 1
        raise self._error("unterminated string")

    def _word(self) -> None:
        start = self.pos
        while self.pos < len(self.text) and self.text[self.pos] not in _WORD_END:
            self.pos += 1
        if self.pos == start:
            found = repr(self._peek()) if self._peek() else "the end of the text"
            raise self._error(f"expected a value, found {found}")

    def _key(self) -> str:
        start = self.pos
        if self._peek() in ('"', "'"):
            self._string()
            return str(json5.loads(self.text[start : self.pos]))
        self._word()
        return self.text[start : self.pos]

    def _expect(self, char: str) -> None:
        if self._peek() != char:
            raise self._error(f"expected '{char}'")
        self.pos += 1

    def _container(self, is_object: bool) -> _Node:
        start = self.pos
        close = "}" if is_object else "]"
        self.pos += 1
        members: List[_Member] = []
        self._skip()
        while self._peek() != close:
            member_start = self.pos
            key = None
            if is_object:
                key = self._key()
                self._skip()
                self._expect(":")
                self._skip()
            value = self._value()
            self._skip()
            comma = None
            if self._peek() == ",":
                comma = self.pos
                self.pos += 1
                self._skip()
            members.append(_Member(key, member_start, value, comma))
            if comma is None and self._peek() != close:
                raise self._error(f"expected ',' or '{close}'")
        self.pos += 1
        return _Node(start, self.pos, members, is_object)


def join_pointer(*tokens: Any) -> str:
    """The JSON Pointer to the value the keys and list indexes lead to."""
    return "".join("/" + str(t).replace("~", "~0").replace("/", "~1") for t in tokens)


def split_pointer(path: str) -> List[str]:
    """The keys and list indexes in a JSON Pointer, unescaped."""
    if path == "":
        return []
    if not path.startswith("/"):
        raise JsonSourceError(f"A path starts with '/': {path!r}")
    return [t.replace("~1", "/").replace("~0", "~") for t in path[1:].split("/")]


class JsonSource:
    """The text of a JSON or JSON5 document, edited one value at a time.

    Every edit checks that the new text parses to the old value with only that
    change, so a scanner mistake raises instead of corrupting the file.

    Attributes:
        text: The current text.
    """

    def __init__(self, text: str) -> None:
        """Scan `text`.

        Raises:
            JsonSourceError: If the text is not JSON or JSON5 the scanner can
                read.
        """
        self.text = text
        self._root = _Scanner(text).parse()

    @property
    def value(self) -> Any:
        """The document as Python data, as json_parser would return it."""
        return self._decode(self._root)

    def replace(self, path: str, value: Any) -> None:
        """Replace the value at `path`."""
        node = self._find(self._split_child(path))
        expected = self._expected("replace", path, value)
        old_text = self.text[node.start : node.end]
        inline = node.members is not None and "\n" not in old_text
        rendered = self._render(value, self._line_indent(node.start), inline)
        self._apply([(node.start, node.end, rendered)], expected)

    def add(self, path: str, value: Any) -> None:
        """Add a value as in JSON Patch: a new key at the end of an object, an
        element at a list index (``-`` for the end), or a replacement for a key
        that exists."""
        *parent_tokens, token = self._split_child(path)
        parent = self._find(parent_tokens)
        members = self._members(parent, path)
        if parent.is_object:
            if any(m.key == token for m in members):
                self.replace(path, value)
                return
            index = len(members)
        else:
            index = len(members) if token == "-" else _list_index(token, path)
            if index > len(members):
                raise JsonSourceError(f"No list position at {path}")
        expected = self._expected("add", path, value)
        key = token if parent.is_object else None
        self._apply(self._insert_edits(parent, index, key, value), expected)

    def remove(self, path: str) -> None:
        """Remove the key or list element at `path` with its comma, and the
        comment lines directly above it."""
        *parent_tokens, token = self._split_child(path)
        parent = self._find(parent_tokens)
        index = self._member_index(parent, token, path)
        expected = self._expected("remove", path)
        self._apply(self._remove_edits(parent, index), expected)

    def _split_child(self, path: str) -> List[str]:
        tokens = split_pointer(path)
        if not tokens:
            raise JsonSourceError("The whole document cannot be added or removed")
        return tokens

    def _members(self, node: _Node, path: str) -> List[_Member]:
        if node.members is None:
            raise JsonSourceError(f"No object or list holds {path}")
        return node.members

    def _member_index(self, node: _Node, token: str, path: str) -> int:
        members = self._members(node, path)
        if node.is_object:
            # json5 keeps the last of two equal keys.
            matches = [i for i, m in enumerate(members) if m.key == token]
            if matches:
                return matches[-1]
        else:
            index = _list_index(token, path)
            if index < len(members):
                return index
        raise JsonSourceError(f"No value at {path}")

    def _find(self, tokens: List[str]) -> _Node:
        node = self._root
        for depth, token in enumerate(tokens):
            path = "/" + "/".join(tokens[: depth + 1])
            node = self._members(node, path)[
                self._member_index(node, token, path)
            ].value
        return node

    def _decode(self, node: _Node) -> Any:
        if node.members is None:
            raw = self.text[node.start : node.end]
            try:
                return json.loads(raw)
            except ValueError:
                return json5.loads(raw)
        if node.is_object:
            return {m.key: self._decode(m.value) for m in node.members}
        return [self._decode(m.value) for m in node.members]

    def _newline(self) -> str:
        return "\r\n" if "\r\n" in self.text else "\n"

    def _indent_unit(self) -> str:
        indents = re.findall(r"(?m)^[ \t]+(?=\S)", self.text)
        return min(indents, key=len) if indents else "    "

    def _line_start(self, pos: int) -> int:
        return self.text.rfind("\n", 0, pos) + 1

    def _line_end(self, pos: int) -> int:
        """Where the line holding `pos` ends, before its line break."""
        end = self.text.find("\n", pos)
        if end < 0:
            return len(self.text)
        return end - 1 if end > pos and self.text[end - 1] == "\r" else end

    def _next_line_start(self, pos: int) -> int:
        end = self.text.find("\n", pos)
        return len(self.text) if end < 0 else end + 1

    def _line_indent(self, pos: int) -> str:
        start = self._line_start(pos)
        match = re.match(r"[ \t]*", self.text[start:pos])
        return match.group(0) if match else ""

    def _starts_line(self, pos: int) -> bool:
        return self.text[self._line_start(pos) : pos].strip() == ""

    def _ends_line(self, pos: int) -> bool:
        """True if only whitespace or a // comment follows `pos` on its line."""
        rest = self.text[pos : self._line_end(pos)].strip()
        return rest == "" or rest.startswith("//")

    def _is_comment_line(self, start: int, end: int) -> bool:
        line = self.text[start:end].strip()
        return line.startswith("//") or (line.startswith("/*") and line.endswith("*/"))

    def _block_start(self, member: _Member) -> int:
        """The start of the member's line, or of the comment lines right above."""
        start = self._line_start(member.start)
        while start > 0:
            above = self._line_start(start - 1)
            if not self._is_comment_line(above, start):
                break
            start = above
        return start

    def _render(self, value: Any, indent: str, inline: bool) -> str:
        if inline:
            return json.dumps(value, ensure_ascii=False)
        text = json.dumps(value, indent=self._indent_unit(), ensure_ascii=False)
        return text.replace("\n", self._newline() + indent)

    def _member_text(
        self,
        key: Optional[str],
        value: Any,
        indent: str,
        inline: bool,
        neighbour: Optional[_Member] = None,
    ) -> str:
        """The key and value text, with the key unquoted if the neighbour's is."""
        if key is None:
            prefix = ""
        elif (
            neighbour is not None
            and self.text[neighbour.start] not in ('"', "'")
            and _IDENTIFIER.fullmatch(key)
        ):
            prefix = key + ": "
        else:
            prefix = json.dumps(key, ensure_ascii=False) + ": "
        return prefix + self._render(value, indent, inline)

    def _insert_edits(
        self, container: _Node, index: int, key: Optional[str], value: Any
    ) -> List[_Edit]:
        members = container.members or []
        if not members:
            return self._fill_empty_edits(container, key, value)
        neighbour = members[min(index, len(members) - 1)]
        one_per_line = self._starts_line(neighbour.start)
        neighbour_text = self.text[neighbour.value.start : neighbour.value.end]
        inline = not one_per_line or (
            neighbour.value.members is not None and "\n" not in neighbour_text
        )
        indent = self._line_indent(neighbour.start)
        member = self._member_text(key, value, indent, inline, neighbour)

        if index < len(members):
            if one_per_line:
                at = self._block_start(neighbour)
                return [(at, at, indent + member + "," + self._newline())]
            return [(neighbour.start, neighbour.start, member + ", ")]

        last = neighbour
        if last.comma is not None:
            after = last.comma + 1
            if not one_per_line:
                return [(after, after, " " + member + ",")]
            at = self._line_end(after) if self._ends_line(after) else after
            return [(at, at, self._newline() + indent + member + ",")]
        after = last.value.end
        if not one_per_line:
            return [(after, after, ", " + member)]
        new_line = self._newline() + indent + member
        if not self._ends_line(after):
            return [(after, after, "," + new_line)]
        line_end = self._line_end(after)
        return [(after, after, ","), (line_end, line_end, new_line)]

    def _fill_empty_edits(
        self, container: _Node, key: Optional[str], value: Any
    ) -> List[_Edit]:
        indent = self._line_indent(container.start)
        inner_indent = indent + self._indent_unit()
        member = self._member_text(key, value, inner_indent, inline=False)
        newline = self._newline()
        # Comments inside the empty brackets stay, before the new member.
        inner = self.text[container.start + 1 : container.end - 1].rstrip()
        body = inner + newline + inner_indent + member + newline + indent
        return [(container.start + 1, container.end - 1, body)]

    def _remove_edits(self, container: _Node, index: int) -> List[_Edit]:
        members = container.members or []
        member = members[index]
        previous = members[index - 1] if index > 0 else None
        end = member.value.end if member.comma is None else member.comma + 1
        if self._starts_line(member.start) and self._ends_line(end):
            start = self._block_start(member)
            stop = self._next_line_start(end)
        elif member.comma is None and previous is not None:
            # The last of several on one line: take the comma before it too.
            return [(previous.value.end, end, "")]
        else:
            start = member.start
            stop = end
            while stop < len(self.text) and self.text[stop] in " \t":
                stop += 1

        inner_left = (
            self.text[container.start + 1 : start] + self.text[stop : container.end - 1]
        )
        if len(members) == 1 and inner_left.strip() == "":
            return [(container.start + 1, container.end - 1, "")]
        edits = [(start, stop, "")]
        # Without its last element, the comma before it would end the list.
        if member.comma is None and previous is not None and previous.comma is not None:
            edits.append((previous.comma, previous.comma + 1, ""))
        return edits

    def _expected(self, op: str, path: str, value: Any = None) -> Any:
        """The document's value after the operation."""
        document = copy.deepcopy(self.value)
        apply_to_data(document, op, path, value)
        return document

    def _apply(self, edits: List[_Edit], expected: Any) -> None:
        # Edits at the same position go in in list order.
        pieces = []
        cursor = 0
        for start, end, replacement in sorted(edits, key=lambda edit: edit[:2]):
            pieces += [self.text[cursor:start], replacement]
            cursor = end
        pieces.append(self.text[cursor:])
        edited = JsonSource("".join(pieces))
        if edited.value != expected:
            raise JsonSourceError(
                "The edit did not give the expected document, so it was not made"
            )
        self.text = edited.text
        self._root = edited._root


def apply_to_data(document: Any, op: str, path: str, value: Any = None) -> None:
    """Make a JSON Patch ``add``, ``replace`` or ``remove`` on Python data.

    Raises:
        JsonSourceError: If `path` does not lead to a place for the operation.
    """
    tokens = split_pointer(path)
    if not tokens:
        raise JsonSourceError("The whole document cannot be added or removed")
    *parent_tokens, token = tokens
    parent = document
    for depth, parent_token in enumerate(parent_tokens):
        prefix = "/" + "/".join(tokens[: depth + 1])
        parent = parent[_existing_slot(parent, parent_token, prefix)]
    if isinstance(parent, dict):
        if op == "add":
            parent[token] = value
            return
        token_slot: Any = _existing_slot(parent, token, path)
    elif isinstance(parent, list):
        if op == "add":
            if token == "-":
                parent.append(value)
                return
            index = _list_index(token, path)
            if index > len(parent):
                raise JsonSourceError(f"No list position at {path}")
            parent.insert(index, value)
            return
        token_slot = _existing_slot(parent, token, path)
    else:
        raise JsonSourceError(f"No object or list holds {path}")
    if op == "replace":
        parent[token_slot] = value
    elif op == "remove":
        del parent[token_slot]
    else:
        raise JsonSourceError(f"Unknown operation {op!r}")


def _list_index(token: str, path: str) -> int:
    if not _ARRAY_INDEX.fullmatch(token):
        raise JsonSourceError(f"No list position at {path}")
    return int(token)


def _existing_slot(parent: Any, token: str, path: str) -> Any:
    """The dict key or list index `token` names in `parent`."""
    if isinstance(parent, dict):
        if token in parent:
            return token
    elif isinstance(parent, list):
        index = _list_index(token, path)
        if index < len(parent):
            return index
    else:
        raise JsonSourceError(f"No object or list holds {path}")
    raise JsonSourceError(f"No value at {path}")
