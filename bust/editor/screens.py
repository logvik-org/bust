"""The dialogs of the editor: forms, questions and lists."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Select, Static

# The choice that removes a key from the file.
NOT_SET = "\0not set"

Values = Dict[str, str]
# Checks the answers of a form and returns bust's message, or None.
Check = Callable[[Values], Optional[str]]


@dataclass
class Item:
    """One question of a form.

    Attributes:
        name: The key of the answer in the form's values.
        label: The text in front of the question.
        default: The answer the form starts with.
        choices: The answers to choose from, as (label, value), or None for a
            question answered with text.
        shown_if: Decides from the other answers whether the question applies.
    """

    name: str
    label: str
    default: str = ""
    choices: Optional[Sequence[Tuple[str, str]]] = None
    shown_if: Optional[Callable[[Values], bool]] = field(default=None)


class FormScreen(ModalScreen[Optional[Values]]):
    """A dialog of questions. OK checks the answers, and the dialog stays open
    with bust's message until they pass. It returns the answers, or None when
    cancelled."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(
        self,
        title: str,
        items: List[Item],
        check: Check,
        note: str = "",
        remove: bool = False,
    ) -> None:
        """Ask the `items`.

        Args:
            title: The heading of the dialog.
            items: The questions.
            check: Checks the answers.
            note: Text under the heading.
            remove: Offer a button that returns ``{"remove": "true"}``.
        """
        super().__init__()
        self.title_text = title
        self.items = items
        self.check = check
        self.note = note
        self.offer_remove = remove

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.title_text, classes="dialog-title")
            if self.note:
                yield Static(self.note, classes="note")
            for item in self.items:
                with Horizontal(classes="form-row", id=f"row-{item.name}"):
                    yield Label(item.label)
                    if item.choices is None:
                        yield Input(item.default, id=item.name)
                    else:
                        yield Select(
                            [(label, value) for label, value in item.choices],
                            value=item.default,
                            allow_blank=False,
                            id=item.name,
                        )
            yield Static("", id="error", markup=False)
            with Horizontal(classes="buttons"):
                yield Button("OK", variant="primary", id="ok")
                if self.offer_remove:
                    yield Button("Remove from the file", variant="warning", id="remove")
                yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self._update_shown()

    def values(self) -> Values:
        answers: Values = {}
        for item in self.items:
            if item.choices is None:
                answers[item.name] = self.query_one(f"#{item.name}", Input).value
            else:
                answers[item.name] = str(self.query_one(f"#{item.name}", Select).value)
        return {
            name: value
            for name, value in answers.items()
            if self._applies(name, answers)
        }

    def _applies(self, name: str, answers: Values) -> bool:
        item = next(item for item in self.items if item.name == name)
        return item.shown_if is None or item.shown_if(answers)

    def _update_shown(self) -> None:
        answers = {}
        for item in self.items:
            widget = self.query_one(f"#{item.name}")
            answers[item.name] = str(getattr(widget, "value"))
        for item in self.items:
            row = self.query_one(f"#row-{item.name}")
            row.display = self._applies(item.name, answers)

    def on_select_changed(self, event: Select.Changed) -> None:
        self.changed(event.select.id or "", str(event.value))
        self._update_shown()

    def changed(self, name: str, value: str) -> None:
        """Called when a choice changes."""

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.submit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        if event.button.id == "ok":
            self.submit()
        elif event.button.id == "remove":
            self.dismiss({"remove": "true"})
        else:
            self.dismiss(None)

    def submit(self) -> None:
        answers = self.values()
        error = self.check(answers)
        if error:
            self.query_one("#error", Static).update(error)
        else:
            self.dismiss(answers)

    def action_cancel(self) -> None:
        self.dismiss(None)


class QuestionScreen(ModalScreen[str]):
    """A question answered with one of a few buttons. It returns the id of the
    button, or "cancel" for Escape."""

    BINDINGS = [Binding("escape", "cancel", "Cancel")]

    def __init__(
        self, question: str, buttons: Sequence[Tuple[str, str]], detail: str = ""
    ) -> None:
        """Ask `question`.

        Args:
            question: The question.
            buttons: Each button as (id, label). The first one is the default.
            detail: Text under the question.
        """
        super().__init__()
        self.question = question
        self.buttons = buttons
        self.detail = detail

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label(self.question, classes="dialog-title")
            if self.detail:
                with VerticalScroll(classes="detail"):
                    yield Static(self.detail, markup=False)
            with Horizontal(classes="buttons"):
                for number, (name, label) in enumerate(self.buttons):
                    if number == 0:
                        yield Button(label, variant="primary", id=name)
                    else:
                        yield Button(label, id=name)

    def on_mount(self) -> None:
        self.query_one(Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id or "cancel")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class ListScreen(ModalScreen[None]):
    """A table of entries in a dialog, with keys to add, change and remove
    them. The owner fills the table and acts on the keys."""

    BINDINGS = [
        Binding("escape", "close", "Close"),
        Binding("a", "add", "Add"),
        Binding("delete,d", "remove", "Remove"),
        Binding("enter", "change", "Change", show=True),
    ]

    def __init__(
        self,
        title: str,
        headers: Sequence[str],
        rows: Callable[[], Sequence[Sequence[Any]]],
        actions: Dict[str, Callable[[Optional[int]], None]],
        note: str = "",
    ) -> None:
        """List `rows`.

        Args:
            title: The heading of the dialog.
            headers: The column headings.
            rows: Gives the rows, called again by `refresh_rows`.
            actions: What "add", "change" and "remove" do, given the row under
                the cursor. "add" gets None.
            note: Text under the heading.
        """
        super().__init__()
        self.title_text = title
        self.headers = headers
        self.rows = rows
        self.actions = actions
        self.note = note

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="wide"):
            yield Label(self.title_text, classes="dialog-title")
            if self.note:
                yield Static(self.note, classes="note")
            yield DataTable(cursor_type="row", id="entries")
            keys = [
                ("a", "add"),
                ("Enter", "change"),
                ("Delete", "remove"),
                ("Escape", "close"),
            ]
            yield Static(
                "   ".join(
                    f"[b]{key}[/b] {what}"
                    for key, what in keys
                    if what == "close" or what in self.actions
                ),
                classes="note",
            )

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*self.headers)
        self.refresh_rows()
        table.focus()

    def refresh_rows(self) -> None:
        table = self.query_one(DataTable)
        row = table.cursor_row
        table.clear()
        for cells in self.rows():
            table.add_row(*(c if isinstance(c, Text) else Text(str(c)) for c in cells))
        if table.row_count:
            table.move_cursor(row=min(row, table.row_count - 1))

    def _row(self) -> Optional[int]:
        table = self.query_one(DataTable)
        return table.cursor_row if table.row_count else None

    def _act(self, name: str, needs_row: bool) -> None:
        row = self._row() if needs_row else None
        if name in self.actions and (row is not None or not needs_row):
            self.actions[name](row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        self._act("change", True)

    def action_add(self) -> None:
        self._act("add", False)

    def action_change(self) -> None:
        self._act("change", True)

    def action_remove(self) -> None:
        self._act("remove", True)

    def action_close(self) -> None:
        self.dismiss(None)


def choices(values: Sequence[str], not_set: bool = False) -> List[Tuple[str, str]]:
    """Select options for `values`, and "not set" if asked for."""
    options = [(value, value) for value in values]
    if not_set:
        options.append(("not set", NOT_SET))
    return options


def default_choice(options: Sequence[Tuple[str, str]], value: Any) -> str:
    """`value` if it is one of the options, else the first option."""
    values = [option for _, option in options]
    text = (
        ""
        if value is None
        else str(value).lower() if isinstance(value, bool) else str(value)
    )
    return text if text in values else values[0]


class TextScreen(ModalScreen[None]):
    """A dialog that shows text until it is closed."""

    BINDINGS = [Binding("escape,enter,question_mark", "close", "Close")]

    def __init__(self, title: str, text: str) -> None:
        """Show `text`, which may use Rich markup."""
        super().__init__()
        self.title_text = title
        self.text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog", classes="wide"):
            yield Label(self.title_text, classes="dialog-title")
            yield Static(self.text)
            with Horizontal(classes="buttons"):
                yield Button("Close", variant="primary", id="close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)

    def action_close(self) -> None:
        self.dismiss(None)
