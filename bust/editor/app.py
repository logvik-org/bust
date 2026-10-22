"""The full-screen register map editor behind ``bust FILE -c`` and ``-e``.

The main screen lists the registers, the fields of the register under the
cursor, and the keys of the register or field in focus. Dialogs ask for new
registers and fields and for new values. Every change goes through EditSession
and RegisterMapDocument, so a dialog shows bust's message and stays open for an
answer bust rejects.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Set

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from rich.text import Text
from textual.widgets import DataTable, Footer, Header, Select, Static

from bust.core.bus import Bus
from bust.core.enums import FieldType, RegisterType
from bust.editing.document import (
    EditRejected,
    FileChanged,
    Operation,
    RegisterMapDocument,
)
from bust.editor.screens import (
    NOT_SET,
    FormScreen,
    Item,
    ListScreen,
    QuestionScreen,
    TextScreen,
    Values,
    choices,
    default_choice,
)
from bust.editor.overview import OverviewScreen
from bust.editor.session import (
    EditSession,
    Property,
    access_choices,
    check_identifier,
    inherited_access,
    number_value,
)

_CSS = """
#status { height: 1; padding: 0 1; background: $boost; }
#left { width: 3fr; }
#right { width: 2fr; }
#hints { height: 1; padding: 0 1; color: $text-muted; }
MainScreen DataTable {
    border: round $panel-lighten-2; border-title-color: $text-muted;
    border-subtitle-color: $text-muted;
}
MainScreen DataTable:focus {
    border: round $accent; border-title-color: $accent; border-title-style: bold;
}
#registers { height: 2fr; }
#fields { height: 1fr; }
#properties { height: 1fr; }
#help { height: auto; min-height: 3; padding: 0 1 1 1; color: $text-muted; }
FormScreen, QuestionScreen, ListScreen { align: center middle; }
#dialog {
    width: 84; height: auto; max-height: 100%; overflow-y: auto;
    border: thick $primary; background: $surface; padding: 1 2;
}
#dialog.wide { width: 100; }
.dialog-title { text-style: bold; padding-bottom: 1; }
.note { color: $text-muted; padding-bottom: 1; }
.detail { height: auto; max-height: 20; padding-bottom: 1; }
.form-row { height: auto; }
.form-row Label { width: 24; padding: 1 1 0 0; }
.form-row Input, .form-row Select { width: 1fr; }
#error { color: $error; height: auto; }
.buttons { height: auto; align-horizontal: right; padding-top: 1; }
.buttons Button { margin-left: 1; }
#entries { height: auto; max-height: 20; }
"""

_DESCRIPTION_LENGTH = 40
_HELP = """\
[b]Moving around[/b]
  [b]Tab[/b], [b]Shift+Tab[/b]   next or previous pane
  [b]1[/b] [b]2[/b] [b]3[/b]            the registers, the fields, the keys
  [b]↑[/b] [b]↓[/b]              move in a pane, or click a row
  [b]Enter[/b]            on a register or field: go to its keys
                   on a key: change it in a dialog
                   on enums: list the enumerated values

[b]Changing the register map[/b]
  [b]a[/b]                add a register
  [b]f[/b]                add a field to the register under the cursor
  [b]Delete[/b], [b]d[/b]        remove the register, or the field whose keys are shown
  [b]m[/b]                the module and bus keys
  [b]g[/b]                give an address to each register without one

[b]Looking and saving[/b]
  [b]o[/b]                overview of the register map, as in the documentation
  [b]s[/b], [b]Ctrl+S[/b]        save
  [b]q[/b], [b]Ctrl+Q[/b]        quit, asking first about unsaved changes

[b]In a dialog[/b]
  [b]Tab[/b] moves between the answers, [b]Enter[/b] or OK takes them, [b]Escape[/b] cancels.
  An answer bust rejects shows bust's message and keeps the dialog open.\
"""
_HINTS = (
    "[b]Tab[/b] or [b]1[/b] [b]2[/b] [b]3[/b] switch pane   [b]↑↓[/b] move   "
    "[b]Enter[/b] open   [b]o[/b] overview   [b]?[/b] all keys"
)


def _shorten(text: str, length: int = _DESCRIPTION_LENGTH) -> str:
    return text if len(text) <= length else text[: length - 3] + "..."


def _cells(row: Any) -> List[Text]:
    """Table cells that show the text as it is, not as markup."""
    return [Text(str(cell)) for cell in row]


def _value(prop: Property) -> Text:
    """The value of a key, dimmed with "(not set)" if the file does not set it."""
    if prop.is_set:
        return Text(prop.value)
    return Text(f"{prop.value} (not set)", style="dim")


class MainScreen(Screen[None]):
    """The registers, the fields of one, and the keys of the one in focus."""

    BINDINGS = [
        Binding("a", "add_register", "Add register"),
        Binding("f", "add_field", "Add field"),
        Binding("delete,d", "remove", "Remove"),
        Binding("m", "edit_module", "Module and bus"),
        Binding("g", "fill_addresses", "Give addresses", show=False),
        Binding("o", "overview", "Overview"),
        Binding("question_mark", "help", "Help"),
        Binding("1", "focus_pane('registers')", "Registers", show=False),
        Binding("2", "focus_pane('fields')", "Fields", show=False),
        Binding("3", "focus_pane('properties')", "Keys", show=False),
        Binding("s,ctrl+s", "save", "Save"),
        Binding("q", "quit_editor", "Quit"),
    ]

    def __init__(self, session: EditSession) -> None:
        super().__init__()
        self.session = session
        self.register: Optional[int] = None
        self.field: Optional[int] = None
        # Whose keys the right pane lists: "register" or "field".
        self.subject = "register"
        self.properties: List[Property] = []
        # What the listed keys belong to, such as "Register ctrl".
        self.owner = ""

    @property
    def editor(self) -> "EditorApp":
        app = self.app
        assert isinstance(app, EditorApp)
        return app

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="status", markup=False)
        yield Static(_HINTS, id="hints")
        with Horizontal():
            with Vertical(id="left"):
                yield DataTable(cursor_type="row", id="registers")
                yield DataTable(cursor_type="row", id="fields")
            with Vertical(id="right"):
                yield DataTable(cursor_type="row", id="properties")
                yield Static("", id="help", markup=False)
        yield Footer()

    def on_mount(self) -> None:
        registers = self.query_one("#registers", DataTable)
        registers.add_columns(
            "Name", "Address", "Type", "Width", "sw", "hw", "Reset", "Description"
        )
        self.query_one("#fields", DataTable).add_columns(
            "Name", "Bits", "Type", "sw", "hw", "Reset", "Description"
        )
        self.query_one("#properties", DataTable).add_columns("Key", "Value")
        registers.border_title = "1 Registers"
        registers.border_subtitle = "Enter: its keys"
        self.query_one("#fields", DataTable).border_subtitle = "Enter: its keys"
        self.query_one("#properties", DataTable).border_subtitle = "Enter: change"
        self.refresh_all()
        registers.focus()

    # Showing the register map.

    def refresh_all(self) -> None:
        """Show the register map as it is now, keeping the cursors."""
        session = self.session
        self.query_one("#status", Static).update(session.status())
        registers = session.registers
        if self.register is not None and self.register >= len(registers):
            self.register = len(registers) - 1 if registers else None
        if self.register is None and registers:
            self.register = 0
        table = self.query_one("#registers", DataTable)
        with self.app.batch_update():
            table.clear()
            for row in session.register_rows():
                table.add_row(*_cells([*row[:-1], _shorten(row[-1])]))
            if self.register is not None:
                table.move_cursor(row=self.register)
            self._refresh_fields()
            self._refresh_properties()

    def _refresh_fields(self) -> None:
        table = self.query_one("#fields", DataTable)
        table.clear()
        index = self.register
        has_fields = (
            index is not None
            and self.session.registers[index].type == RegisterType.FIELDS
        )
        table.display = has_fields
        if not has_fields or index is None:
            self.field = None
            if self.subject == "field":
                self.subject = "register"
            return
        name = self.session.registers[index].name
        table.border_title = f"2 Fields of {name}"
        rows = self.session.field_rows(index)
        for row in rows:
            table.add_row(*_cells([*row[:-1], _shorten(row[-1])]))
        if self.field is None or self.field >= len(rows):
            self.field = 0
        table.move_cursor(row=self.field)

    def _refresh_properties(self) -> None:
        table = self.query_one("#properties", DataTable)
        row = table.cursor_row
        table.clear()
        session = self.session
        if self.register is None:
            self.properties = []
            table.border_title = "3 Keys"
            self.query_one("#help", Static).update("Press a to add a register.")
            return
        if self.subject == "field" and self.field is not None:
            field = session.field_of(self.register, self.field)
            self.owner = (
                f"Field {field.name} of {session.registers[self.register].name}"
            )
            self.properties = session.field_properties(self.register, self.field)
        else:
            register = session.registers[self.register]
            self.owner = f"Register {register.name}"
            self.properties = session.register_properties(self.register)
        table.border_title = f"3 {self.owner}"
        for prop in self.properties:
            table.add_row(Text(prop.label), _value(prop))
        if self.subject == "field" and self.field is not None:
            count = len(session.enum_rows(self.register, self.field))
            table.add_row("enums", f"{count} value{'' if count == 1 else 's'}")
        if table.row_count:
            table.move_cursor(row=min(row, table.row_count - 1))
        self._show_help()

    def _show_help(self) -> None:
        table = self.query_one("#properties", DataTable)
        row = table.cursor_row
        help_text = "Enter changes the key under the cursor."
        if 0 <= row < len(self.properties):
            prop = self.properties[row]
            help_text = prop.description
            if not prop.is_set:
                help_text += " Not set in the file, so bust uses the value shown."
        elif table.row_count:
            help_text = "The named values of the field. Enter lists them."
        self.query_one("#help", Static).update(help_text)

    # Following the cursor.

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        name = event.data_table.id
        if name == "registers" and event.cursor_row != self.register:
            self.register = event.cursor_row
            self.field = None
            self.subject = "register"
            self._refresh_fields()
            self._refresh_properties()
        elif name == "fields" and event.cursor_row != self.field:
            self.field = event.cursor_row
            if self.subject == "field":
                self._refresh_properties()
        elif name == "properties":
            self._show_help()

    def on_descendant_focus(self, event: Any) -> None:
        widget = getattr(event, "widget", None)
        name = getattr(widget, "id", None)
        subject = {"registers": "register", "fields": "field"}.get(name or "")
        if subject and subject != self.subject:
            self.subject = subject
            self._refresh_properties()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        name = event.data_table.id
        if name in ("registers", "fields"):
            self.query_one("#properties", DataTable).focus()
        elif name == "properties":
            self._edit_property(event.cursor_row)

    # Changing the register map.

    def _edit_property(self, row: int) -> None:
        if self.register is None:
            return
        if row >= len(self.properties):
            if self.field is not None:
                self.editor.edit_enums(self.register, self.field)
            return
        prop = self.properties[row]
        if prop.definition == "register" and prop.key == "type":
            self._change_register_type(self.register)
        else:
            self.editor.edit_property(prop, self.owner)

    def _change_register_type(self, index: int) -> None:
        session = self.session
        register = session.registers[index]
        old = register.type.value
        note = "Changing the type removes the keys the new type does not use."
        if register.type == RegisterType.FIELDS:
            note += f" Another type removes the fields of {register.name}."
        else:
            note += " A fields register asks for its first field next."
        note += (
            " hash and version remove the access keys and the reset, which bust sets."
        )
        types = RegisterType.valid_values()

        def check(values: Values) -> Optional[str]:
            if values["type"] == RegisterType.FIELDS.value:
                return None
            return self.editor.check(
                session.register_type_operations(index, values["type"])
            )

        def done(values: Optional[Values]) -> None:
            if values is None or values["type"] == old:
                return
            if values["type"] != RegisterType.FIELDS.value:
                self.editor.apply(
                    session.register_type_operations(index, values["type"])
                )
                return
            self.editor.ask_field(
                f"The first field of {register.name}",
                session.access_of(index),
                [],
                0,
                lambda field: session.register_type_operations(
                    index, RegisterType.FIELDS.value, field
                ),
            )

        self.app.push_screen(
            FormScreen(
                f"Register {register.name}: type",
                [Item("type", "type", old, choices(types))],
                check,
                note,
            ),
            done,
        )

    def action_add_register(self) -> None:
        self.editor.add_register()

    def action_add_field(self) -> None:
        index = self.register
        if index is None or self.session.registers[index].type != RegisterType.FIELDS:
            self.app.notify(
                "Fields belong to a register of type fields. Change the type of "
                "the register first.",
                severity="warning",
            )
            return
        register = self.session.registers[index]
        self.editor.ask_field(
            f"A new field of {register.name}",
            self.session.access_of(index),
            [field.name for field in register.fields],
            self.session.next_bit(index),
            lambda field: self.session.add_field_operations(index, field),
            self._show_last_field,
        )

    def _show_last_field(self) -> None:
        if self.register is not None:
            self.field = len(self.session.registers[self.register].fields) - 1
            self.refresh_all()

    def action_remove(self) -> None:
        index = self.register
        if index is None:
            return
        session = self.session
        if self.subject == "field" and self.field is not None:
            number = self.field
            what = f"field {session.field_of(index, number).name}"
            operations = session.remove_field_operations(index, number)
        else:
            what = f"register {session.registers[index].name}"
            operations = session.remove_register_operations(index)

        def done(answer: Optional[str]) -> None:
            if answer == "remove":
                self.editor.apply(operations)

        self.app.push_screen(
            QuestionScreen(
                f"Remove {what}?", [("remove", "Remove"), ("cancel", "Cancel")]
            ),
            done,
        )

    def action_edit_module(self) -> None:
        self.editor.edit_module()

    def action_fill_addresses(self) -> None:
        operations = self.session.fill_address_operations()
        if not operations:
            self.app.notify("Every register has an address.")
        elif self.editor.apply(operations):
            self.app.notify(f"Gave {len(operations)} registers their address.")

    def action_save(self) -> None:
        self.editor.save()

    def action_overview(self) -> None:
        self.app.push_screen(OverviewScreen(self.session.document.module))

    def action_help(self) -> None:
        self.app.push_screen(TextScreen("Keys", _HELP))

    def action_focus_pane(self, name: str) -> None:
        table = self.query_one(f"#{name}", DataTable)
        if table.display:
            table.focus()
        elif name == "fields":
            self.app.notify("The register under the cursor has no fields.")

    def action_quit_editor(self) -> None:
        self.editor.quit_editor()


class EditorApp(App[Optional[str]]):
    """Creates or edits one register map file. It returns a message if the
    register map could not be edited."""

    CSS = _CSS
    TITLE = "bust"
    BINDINGS = [Binding("ctrl+q", "quit_editor", "Quit", show=False, priority=True)]

    def __init__(
        self,
        path: str,
        session: Optional[EditSession] = None,
        conversion: Optional[List[str]] = None,
        conversion_operations: Optional[List[Operation]] = None,
    ) -> None:
        """Edit the register map in `path`.

        Args:
            path: The file the register map is saved to.
            session: The register map to edit, or None to create one.
            conversion: The changes that convert a bust 0.14 file, if any.
            conversion_operations: The operations that make them.
        """
        super().__init__()
        self.path = path
        self.session = session
        self.conversion = conversion or []
        self.conversion_operations = conversion_operations or []
        self.sub_title = path
        # bust warns about the whole register map on every change, so each
        # warning is shown once.
        self._warnings_shown: Set[str] = set()

    def on_mount(self) -> None:
        if self.session is None:
            self._ask_new_map()
        elif self.conversion_operations:
            self._ask_conversion()
        else:
            self._start(self.session, [])

    def _start(self, session: EditSession, operations: List[Operation]) -> None:
        self.session = session
        try:
            warnings = session.document.apply(operations)
        except EditRejected as error:
            self.exit(f"bust rejects {self.path}: {error}")
            return
        self.push_screen(MainScreen(session))
        self._show_warnings(warnings)
        if not session.document.keeps_formatting:
            self.notify(
                "bust cannot edit this file in place, so saving rewrites it as "
                "plain JSON without comments.",
                severity="warning",
                timeout=10,
            )

    @property
    def main(self) -> MainScreen:
        for screen in self.screen_stack:
            if isinstance(screen, MainScreen):
                return screen
        raise RuntimeError("The editor has not started")

    # Starting.

    def _ask_conversion(self) -> None:
        assert self.session is not None
        session = self.session

        def done(answer: Optional[str]) -> None:
            if answer == "convert":
                self._start(session, self.conversion_operations)
            else:
                self.exit()

        self.push_screen(
            QuestionScreen(
                f"{os.path.basename(self.path)} is in the bust 0.14 format",
                [("convert", "Convert"), ("quit", "Quit")],
                "The editor converts it. The file changes when you save.\n\n"
                + "\n".join(f"• {change}" for change in self.conversion),
            ),
            done,
        )

    def _ask_new_map(self) -> None:
        stem = os.path.splitext(os.path.basename(self.path))[0]
        buses = Bus.supported_bus

        def has_data_width(values: Values) -> bool:
            return not Bus.BUS_CONFIG[values["bus"]]["fixed_data_width"]

        class NewMapForm(FormScreen):
            def changed(self, name: str, value: str) -> None:
                if name == "bus":
                    byte = Bus.BUS_CONFIG[value]["byte_addressable"]
                    choice = self.query_one("#byte_addressable", Select)
                    choice.value = str(byte).lower()

        def module_of(values: Values) -> Dict[str, Any]:
            return {
                "name": values["name"].strip(),
                "version": values["version"],
                "description": values["description"],
                "byte_addressable": values["byte_addressable"] == "true",
            }

        def make(values: Values) -> RegisterMapDocument:
            return EditSession.new_document(
                values["bus"],
                values["addr_width"],
                values.get("data_width", ""),
                module_of(values),
            )

        def check(values: Values) -> Optional[str]:
            try:
                make(values)
            except Exception as error:
                return str(error)
            return None

        def done(values: Optional[Values]) -> None:
            if values is None:
                self.exit()
                return
            self._start(EditSession(make(values), self.path), [])
            self.add_register()

        byte = str(Bus.BUS_CONFIG["axi"]["byte_addressable"]).lower()
        self.push_screen(
            NewMapForm(
                f"A new register map in {self.path}",
                [
                    Item("bus", "Bus", "axi", choices(buses)),
                    Item("addr_width", "Address width (bits)", "32"),
                    Item(
                        "data_width", "Data width (bits)", "32", shown_if=has_data_width
                    ),
                    Item("name", "Module name", stem),
                    Item("version", "Version", "1.0"),
                    Item("description", "Description"),
                    Item(
                        "byte_addressable",
                        "Addresses count bytes",
                        byte,
                        choices(["true", "false"]),
                    ),
                ],
                check,
                "byte_addressable true: an address counts bytes. false: it counts "
                "data words.",
            ),
            done,
        )

    # Changes, used by the screens.

    def check(self, operations: List[Operation]) -> Optional[str]:
        """bust's message about the operations, or None if it accepts them."""
        assert self.session is not None
        try:
            self.session.document.check_operations(operations)
        except EditRejected as error:
            return str(error)
        return None

    def apply(self, operations: List[Operation]) -> bool:
        """Make the change, or show why bust rejects it."""
        assert self.session is not None
        try:
            warnings = self.session.document.apply(operations)
        except EditRejected as error:
            self.notify(
                f"Not changed: {error}", severity="error", timeout=10, markup=False
            )
            return False
        self._show_warnings(warnings)
        self.main.refresh_all()
        return True

    def _show_warnings(self, warnings: List[str]) -> None:
        for warning in warnings:
            if warning not in self._warnings_shown:
                self.notify(
                    warning,
                    title="Warning",
                    severity="warning",
                    timeout=10,
                    markup=False,
                )
                self._warnings_shown.add(warning)

    def edit_property(
        self,
        prop: Property,
        owner: str,
        after: Optional[Callable[[], None]] = None,
    ) -> None:
        """Ask for a new value of a key, or whether to remove it.

        Args:
            prop: The key.
            owner: What the key belongs to, such as "Register ctrl".
            after: Called when the dialog closes.
        """
        session = self.session
        assert session is not None
        options = prop.choices
        if options is not None:
            current = prop.current if prop.is_set else NOT_SET
            values = choices(options, prop.removable or not prop.is_set)
            item = Item("value", prop.key, default_choice(values, current), values)
        else:
            current = "" if prop.current is None else str(prop.current)
            item = Item("value", prop.key, current if prop.is_set else prop.value)

        def operations(values: Values) -> List[Operation]:
            if "remove" in values:
                return session.set_operations(prop, None)
            value: Optional[str] = values["value"]
            if value == NOT_SET:
                value = None
            return session.set_operations(prop, value)

        def check(values: Values) -> Optional[str]:
            try:
                return self.check(operations(values))
            except Exception as error:
                return str(error)

        def done(values: Optional[Values]) -> None:
            if values is not None:
                self.apply(operations(values))
            if after is not None:
                after()

        self.push_screen(
            FormScreen(
                f"{owner}: {prop.label}",
                [item],
                check,
                prop.description,
                remove=options is None and prop.removable,
            ),
            done,
        )

    def add_register(self) -> None:
        """Ask for a register, giving it every key the format recommends."""
        session = self.session
        assert session is not None
        taken = [reg.name for reg in session.registers]
        types = RegisterType.valid_values()
        data_width = str(session.document.module.data_width)

        def register_of(values: Values) -> Dict[str, Any]:
            register: Dict[str, Any] = {
                "name": values["name"].strip(),
                "address": number_value("address", values["address"]),
                "type": values["type"],
            }
            if "width" in values:
                register["width"] = number_value("width", values["width"])
            if "sw" in values:
                register["sw"] = values["sw"]
                register["hw"] = values["hw"]
            if "reset" in values:
                register["reset"] = number_value("reset", values["reset"])
            register["description"] = values["description"]
            return register

        def check(values: Values) -> Optional[str]:
            try:
                check_identifier(values["name"].strip(), taken)
                register = register_of(values)
            except Exception as error:
                return str(error)
            if register["type"] == RegisterType.FIELDS.value:
                # A fields register without fields is rejected, so the rest is
                # checked on a register without fields.
                register = {**register, "type": RegisterType.DEFAULT.value}
            return self.check(session.add_register_operations(register))

        def done(values: Optional[Values]) -> None:
            if values is None:
                return
            register = register_of(values)
            if register["type"] != RegisterType.FIELDS.value:
                if self.apply(session.add_register_operations(register)):
                    self.main.register = len(session.registers) - 1
                    self.main.refresh_all()
                return

            def with_field(field: Dict[str, Any]) -> List[Operation]:
                value = {k: v for k, v in register.items() if k != "description"}
                value["fields"] = [field]
                value["description"] = register["description"]
                return session.add_register_operations(value)

            def added() -> None:
                self.main.register = len(session.registers) - 1
                self.main.refresh_all()

            self.ask_field(
                f"The first field of {register['name']}",
                {"sw": register["sw"], "hw": register["hw"]},
                [],
                0,
                with_field,
                added,
            )

        def is_vector(values: Values) -> bool:
            return values["type"] == RegisterType.VECTOR.value

        def has_access(values: Values) -> bool:
            # bust sets the access and the value of a hash or version register.
            return not RegisterType(values["type"]).is_constant

        def has_reset(values: Values) -> bool:
            return values["type"] != RegisterType.FIELDS.value and has_access(values)

        self.push_screen(
            FormScreen(
                "A new register",
                [
                    Item("name", "Name"),
                    Item("address", "Address", session.next_address()),
                    Item("type", "Type", RegisterType.DEFAULT.value, choices(types)),
                    Item("width", "Width (bits)", data_width, shown_if=is_vector),
                    Item(
                        "sw",
                        "Software access (sw)",
                        "rw",
                        choices(access_choices("sw")),
                        shown_if=has_access,
                    ),
                    Item(
                        "hw",
                        "Hardware access (hw)",
                        "r",
                        choices(access_choices("hw")),
                        shown_if=has_access,
                    ),
                    Item("reset", "Reset value", "0x0", shown_if=has_reset),
                    Item("description", "Description"),
                ],
                check,
                "Change the other keys, such as onwrite, in the list of keys once "
                "the register is added.",
            ),
            done,
        )

    def ask_field(
        self,
        title: str,
        access: Dict[str, Any],
        taken: List[str],
        next_bit: int,
        operations_for: Callable[[Dict[str, Any]], List[Operation]],
        after: Optional[Callable[[], None]] = None,
    ) -> None:
        """Ask for a field, and add it with the operations made from it. The
        field gets sw and hw only where they differ from the register's
        `access`."""
        inherited = {key: inherited_access(access, key) for key in ("sw", "hw")}

        def field_of(values: Values) -> Dict[str, Any]:
            field: Dict[str, Any] = {
                "name": values["name"].strip(),
                "type": values["type"],
                "position": number_value("position", values["position"]),
            }
            if "width" in values:
                field["width"] = number_value("width", values["width"])
            for key in ("sw", "hw"):
                if values[key] != inherited[key]:
                    field[key] = values[key]
            field["reset"] = number_value("reset", values["reset"])
            field["description"] = values["description"]
            return field

        def check(values: Values) -> Optional[str]:
            try:
                check_identifier(values["name"].strip(), taken)
                return self.check(operations_for(field_of(values)))
            except Exception as error:
                return str(error)

        def done(values: Optional[Values]) -> None:
            if values is not None and self.apply(operations_for(field_of(values))):
                if after is not None:
                    after()

        def is_vector(values: Values) -> bool:
            return values["type"] == FieldType.VECTOR.value

        types = FieldType.valid_values()
        self.push_screen(
            FormScreen(
                title,
                [
                    Item("name", "Name"),
                    Item("type", "Type", FieldType.BIT.value, choices(types)),
                    Item("position", "Lowest bit", str(next_bit)),
                    Item("width", "Width (bits)", "2", shown_if=is_vector),
                    Item(
                        "sw",
                        "Software access (sw)",
                        inherited["sw"],
                        choices(access_choices("sw")),
                    ),
                    Item(
                        "hw",
                        "Hardware access (hw)",
                        inherited["hw"],
                        choices(access_choices("hw")),
                    ),
                    Item("reset", "Reset value", "0x0"),
                    Item("description", "Description"),
                ],
                check,
                "sw and hw are written only where they differ from the register's.",
            ),
            done,
        )

    def edit_enums(self, index: int, number: int) -> None:
        """List the enumerated values of a field, to add, change and remove."""
        session = self.session
        assert session is not None
        field = session.field_of(index, number)
        screen: Optional[ListScreen] = None

        def ask(row: Optional[int]) -> None:
            rows = session.enum_rows(index, number)
            taken = [name for i, (name, _) in enumerate(rows) if i != row]
            name, value = rows[row] if row is not None else ("", str(len(rows)))

            def entry_of(values: Values) -> Dict[str, Any]:
                return {
                    "name": values["name"].strip(),
                    "value": number_value("value", values["value"]),
                }

            def check(values: Values) -> Optional[str]:
                try:
                    check_identifier(values["name"].strip(), taken)
                    entry = entry_of(values)
                    return self.check(
                        session.enum_operations(index, number, entry, row)
                    )
                except Exception as error:
                    return str(error)

            def done(values: Optional[Values]) -> None:
                if values is not None:
                    self.apply(
                        session.enum_operations(index, number, entry_of(values), row)
                    )
                    assert screen is not None
                    screen.refresh_rows()

            self.push_screen(
                FormScreen(
                    (
                        "An enumerated value"
                        if row is None
                        else f"Enumerated value {name}"
                    ),
                    [Item("name", "Name", name), Item("value", "Value", value)],
                    check,
                ),
                done,
            )

        def remove(row: Optional[int]) -> None:
            if row is not None and self.apply(
                session.enum_operations(index, number, None, row)
            ):
                assert screen is not None
                screen.refresh_rows()

        screen = ListScreen(
            f"Enumerated values of field {field.name}",
            ("Name", "Value"),
            lambda: session.enum_rows(index, number),
            {"add": ask, "change": ask, "remove": remove},
            "A field with enumerated values is a VHDL enumeration type in to_hw "
            "and from_hw.",
        )
        self.push_screen(screen)

    def edit_module(self) -> None:
        """List the module and bus keys, to change them."""
        session = self.session
        assert session is not None
        screen: Optional[ListScreen] = None

        def rows() -> List[Any]:
            return [(Text(p.label), _value(p)) for p in session.module_properties()]

        def change(row: Optional[int]) -> None:
            if row is None:
                return
            assert screen is not None
            self.edit_property(
                session.module_properties()[row], "Module and bus", screen.refresh_rows
            )

        screen = ListScreen(
            "Module and bus",
            ("Key", "Value"),
            rows,
            {"change": change},
        )
        self.push_screen(screen)

    def save(self, then_quit: bool = False) -> None:
        """Save if the register map changed."""
        session = self.session
        assert session is not None
        document = session.document
        if not document.is_modified:
            self.notify("There are no changes to save.")
            if then_quit:
                self.exit()
            return

        def write() -> None:
            try:
                document.save(self.path)
            except (FileChanged, FileExistsError, OSError) as error:
                self.notify(
                    f"Not saved: {error}", severity="error", timeout=10, markup=False
                )
                return
            self.notify(f"Saved {self.path}.", markup=False)
            self.main.refresh_all()
            if then_quit:
                self.exit()

        if document.keeps_formatting:
            write()
            return

        def answered(answer: Optional[str]) -> None:
            if answer == "save":
                write()

        self.push_screen(
            QuestionScreen(
                f"Saving rewrites {self.path} as plain JSON without comments.",
                [("save", "Save"), ("cancel", "Cancel")],
            ),
            answered,
        )

    def quit_editor(self) -> None:
        """Quit, asking first about unsaved changes."""
        if self.session is None or not self.session.document.is_modified:
            self.exit()
            return

        def answered(answer: Optional[str]) -> None:
            if answer == "save":
                self.save(then_quit=True)
            elif answer == "discard":
                self.exit()

        self.push_screen(
            QuestionScreen(
                "There are unsaved changes.",
                [
                    ("save", "Save and quit"),
                    ("discard", "Quit without saving"),
                    ("cancel", "Back to the editor"),
                ],
            ),
            answered,
        )

    def action_quit_editor(self) -> None:
        self.quit_editor()
