"""The screen that shows the whole register map, as the documentation does."""

from typing import List

from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

from bust.core.enums import RegisterType
from bust.core.module import Module
from bust.editor.diagram import bit_diagram
from bust.generators.register_layout import (
    field_notes,
    register_heading,
    register_list,
)


class OverviewScreen(Screen[None]):
    """The register list, then each register with its bit diagram, its reset
    values and its fields. Enter on the list moves to that register."""

    BINDINGS = [
        Binding("escape,o,q", "close", "Back to the editor"),
        Binding("t", "app.toggle_theme", "Light/dark"),
    ]

    DEFAULT_CSS = """
    OverviewScreen #overview { overflow-x: auto; padding: 0 1; }
    OverviewScreen .heading { text-style: bold; color: $accent; padding-top: 1; }
    OverviewScreen .section { text-style: bold; padding-top: 1; }
    OverviewScreen .muted { color: $text-muted; }
    OverviewScreen .diagram { width: auto; padding-top: 1; }
    OverviewScreen #register-list { height: auto; width: auto; }
    OverviewScreen .register { height: auto; width: auto; }
    """

    def __init__(self, module: Module) -> None:
        super().__init__()
        self.module = module

    def compose(self) -> ComposeResult:
        module = self.module
        yield Header()
        with VerticalScroll(id="overview"):
            yield Static(Text(module.name, style="bold"), classes="heading")
            info = []
            if module.version:
                info.append(f"Version: {module.version}")
            info.append(f"Register map hash: 0x{module.regmap_hash_hex}")
            info.append(
                f"{module.bus.bus_type}, {module.bus.addr_width}-bit addresses, "
                f"{module.data_width}-bit data"
            )
            yield Static("\n".join(info), classes="muted", markup=False)
            if module.description:
                yield Static(module.description, markup=False)
            yield Static("Register list", classes="section")
            yield DataTable(cursor_type="row", id="register-list")
            yield Static("Registers", classes="section")
            for index, register in enumerate(module.registers):
                with Vertical(classes="register", id=f"register-{index}"):
                    name, address = register_heading(register)
                    yield Static(
                        Text.assemble((name, "bold"), "   ", (address, "")),
                        classes="heading",
                    )
                    if register.description:
                        yield Static(register.description, markup=False)
                    lines: List[str] = bit_diagram(register, module.data_width)
                    lines[-1] += "  Reset"
                    yield Static("\n".join(lines), classes="diagram", markup=False)
                    if register.type == RegisterType.FIELDS:
                        notes = Text()
                        for field, note in field_notes(register):
                            notes.append(f"  {field}", style="bold")
                            notes.append(f"  {note}\n")
                        notes.rstrip()
                        yield Static(notes)
        yield Static(
            "[b]↑↓[/b] move   [b]Enter[/b] go to the register   "
            "[b]Escape[/b] back to the editor",
            id="hints",
        )
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#register-list", DataTable)
        headers, rows = register_list(self.module)
        table.add_columns(*headers)
        for row in rows:
            table.add_row(*(Text(cell) for cell in row))
        table.focus()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        event.stop()
        section = self.query_one(f"#register-{event.cursor_row}")
        self.query_one("#overview", VerticalScroll).scroll_to_widget(section, top=True)

    def action_close(self) -> None:
        self.dismiss(None)
