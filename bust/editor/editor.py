"""The interactive register map editor behind ``bust FILE -c`` and ``bust FILE -e``.

The editor asks plain numbered questions, so it needs no curses and runs on any
terminal. Every change goes through RegisterMapDocument, so the editor cannot
save a register map bust rejects, and it writes the file only when the register
map changed. The allowed values and defaults of each key come from the JSON
Schema in bust.schema.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from bust.core.bus import Bus
from bust.core.enums import FieldType, RegisterType
from bust.core.register import Register
from bust.editing.document import (
    EditRejected,
    FileChanged,
    Operation,
    RegisterMapDocument,
)
from bust.editing.json_source import join_pointer
from bust.core.field import INHERITABLE_ACCESS
from bust.editor.utilities import Prompts, shorten, shown, table
from bust.exceptions import FormatError
from bust.interaction import ConsoleInteractionHandler, InteractionHandler
from bust.schema import register_map_schema
from bust.validation.config_validator import parse_number

_SCHEMA = register_map_schema()["$defs"]
# Written as "0x..." strings, the form bust's own files use.
_HEX_KEYS = ("address", "reset")
_UNSET = "-"
# Model attributes named differently from their key.
_ATTRIBUTES = {"position": "pos_low"}


def _register_path(index: Union[int, str], *keys: Any) -> str:
    return join_pointer("module", "register", index, *keys)


def _field_path(register: int, field: Union[int, str], *keys: Any) -> str:
    return _register_path(register, "fields", field, *keys)


def _number_value(key: str, number: int) -> Any:
    return hex(number) if key in _HEX_KEYS else number


class Editor:
    """Creates or edits one register map file through numbered menus."""

    def __init__(
        self,
        document: RegisterMapDocument,
        path: str,
        ask: Optional[InteractionHandler] = None,
        show: Callable[[str], None] = print,
    ) -> None:
        """Edit `document`, which saves to `path`.

        Args:
            document: The register map, already checked.
            path: The file the register map is saved to.
            ask: Answers the questions. Defaults to reading the terminal.
            show: Prints a line.
        """
        self.document = document
        self.path = path
        self.prompts = Prompts(ask or ConsoleInteractionHandler(), show)
        self.show = show
        # bust warns about the whole register map on every change, so each
        # warning is shown once.
        self._warnings_shown: Set[str] = set()

    @classmethod
    def create(
        cls,
        path: str,
        ask: Optional[InteractionHandler] = None,
        show: Callable[[str], None] = print,
    ) -> "Editor":
        """Ask for the bus and module, and start a register map for `path`.

        Raises:
            FileExistsError: If `path` exists.
        """
        if os.path.exists(path):
            raise FileExistsError(f"{path} exists. Edit it with bust {path} -e.")
        prompts = Prompts(ask or ConsoleInteractionHandler(), show)
        show(f"A new register map in {path}.")
        bus = cls._ask_bus(prompts)
        stem = os.path.splitext(os.path.basename(path))[0]
        module = {
            "name": prompts.identifier("Module name", [], stem),
            "version": prompts.text("Version", "1.0"),
            "description": prompts.text("Description", ""),
            "byte_addressable": prompts.yes(
                "Do addresses count bytes, not data words (byte_addressable)?",
                Bus.BUS_CONFIG[bus["type"]]["byte_addressable"],
            ),
        }
        editor = cls(RegisterMapDocument.new(bus, module), path, ask, show)
        if prompts.yes("Add the first register now?", True):
            editor.add_register()
        return editor

    @staticmethod
    def _ask_bus(prompts: Prompts) -> Dict[str, Any]:
        while True:
            types = Bus.supported_bus
            bus_type = types[prompts.choose("Bus", types, types.index("axi"))]
            config = Bus.BUS_CONFIG[bus_type]
            addr_width = prompts.number("Address width in bits", "32")
            data_width = config["fixed_data_width"] or prompts.number(
                "Data width in bits", "32"
            )
            bus = {"type": bus_type, "addr_width": addr_width, "data_width": data_width}
            try:
                Bus(bus)
                return bus
            except FormatError as error:
                prompts.show(str(error))

    @classmethod
    def open(
        cls,
        path: str,
        ask: Optional[InteractionHandler] = None,
        show: Callable[[str], None] = print,
    ) -> Optional["Editor"]:
        """Read `path`. A bust 0.14 register map opens only converted.

        Returns:
            The editor, or None if the user did not convert the file.

        Raises:
            EditRejected: If bust rejects the register map.
        """
        prompts = Prompts(ask or ConsoleInteractionHandler(), show)
        document = RegisterMapDocument.open(path)
        changes, operations = document.legacy_conversion()
        if operations:
            show(f"{path} is in the bust 0.14 format. The editor converts it:")
            for change in changes:
                show(f"  - {change}")
            if not prompts.yes("Convert it? The file changes when you save.", True):
                return None
        editor = cls(document, path, ask, show)
        editor._show_warnings(document.apply(operations))
        if not document.keeps_formatting:
            show(
                "bust cannot edit this file in place, so saving rewrites it as "
                "plain JSON without comments."
            )
        return editor

    def run(self) -> None:
        """Show the main menu until the user quits."""
        actions: List[Tuple[str, Callable[[], Any]]] = [
            ("List registers", self.list_registers),
            ("Add a register", self.add_register),
            ("Edit a register", self.edit_register),
            ("Remove a register", self.remove_register),
            ("Edit the module and bus", self.edit_module),
            ("Give an address to each register without one", self.fill_addresses),
            ("Save", self.save),
        ]
        while True:
            self.show("")
            self.show(self._status())
            labels = [label for label, _ in actions] + ["Quit"]
            try:
                choice = self.prompts.choose("Menu", labels)
                if choice == len(actions):
                    if self._confirm_quit():
                        return
                    continue
                actions[choice][1]()
            except KeyboardInterrupt:
                self.show("\nCancelled.")
            except EOFError:
                self.show("\nNo more input. Unsaved changes are lost.")
                return

    def _status(self) -> str:
        module = self.document.module
        bus = module.bus
        saved = "unsaved changes" if self.document.is_modified else "saved"
        return (
            f"{self.path}: module {module.name}, {bus.bus_type}, "
            f"{bus.addr_width}-bit addresses, {bus.data_width}-bit data, "
            f"registers: {len(module.registers)}, {saved}"
        )

    def _confirm_quit(self) -> bool:
        if not self.document.is_modified:
            return True
        choice = self.prompts.choose(
            "There are unsaved changes",
            ["Save and quit", "Quit without saving", "Back to the menu"],
        )
        if choice == 0:
            return self.save()
        return choice == 1

    def _apply(self, operations: List[Operation]) -> bool:
        """Make the change, or show why bust rejects it."""
        try:
            warnings = self.document.apply(operations)
        except EditRejected as error:
            self.show(f"Not changed: {error}")
            return False
        self._show_warnings(warnings)
        return True

    def _show_warnings(self, warnings: List[str]) -> None:
        for warning in warnings:
            if warning not in self._warnings_shown:
                self.show(f"Warning: {warning}")
                self._warnings_shown.add(warning)

    @property
    def _data(self) -> Any:
        return self.document.data

    def _registers(self) -> List[Register]:
        return self.document.module.registers

    def list_registers(self) -> None:
        """Show every register in a table."""
        registers = self._registers()
        if not registers:
            self.show("There are no registers.")
            return
        rows = [
            (
                index,
                reg.name,
                hex(reg.address),
                reg.type.value,
                reg.width,
                reg.sw.value,
                reg.hw.value,
                reg.reset,
                shorten(reg.description),
            )
            for index, reg in enumerate(registers, start=1)
        ]
        headers = ("#", "Name", "Address", "Type", "Width", "sw", "hw", "Reset")
        self.show(table(headers + ("Description",), rows))

    def _pick(self, what: str, names: List[str]) -> Optional[int]:
        """The index of the entry named or numbered, or None to cancel."""
        while True:
            answer = self.prompts.text(f"{what} (number or name, Enter to cancel)")
            if answer == "":
                return None
            if answer.isdigit() and 1 <= int(answer) <= len(names):
                return int(answer) - 1
            if answer in names:
                return names.index(answer)
            self.show(f"There is no {what.lower()} {answer}.")

    def _pick_register(self) -> Optional[int]:
        self.list_registers()
        if not self._registers():
            return None
        return self._pick("Register", [reg.name for reg in self._registers()])

    def add_register(self) -> None:
        """Ask for a register, giving it every key the format recommends.

        Each answer is checked as soon as it is given, so a rejected answer is
        asked again instead of losing the others.
        """
        prompts = self.prompts
        taken = [reg.name for reg in self._registers()]
        register: Dict[str, Any] = {"name": prompts.identifier("Name", taken)}

        def adding(**keys: Any) -> List[Operation]:
            value = {**register, **keys}
            return [{"op": "add", "path": _register_path("-"), "value": value}]

        next_address = hex(self.document.next_free_address())
        register["address"] = self._ask_until_accepted(
            lambda: hex(prompts.number("Address", next_address)),
            lambda address: adding(address=address),
        )
        types = RegisterType.valid_values()
        register["type"] = types[prompts.choose("Type", types)]
        is_fields = register["type"] == RegisterType.FIELDS.value
        if register["type"] == RegisterType.VECTOR.value:
            data_width = str(self.document.module.data_width)
            register["width"] = self._ask_until_accepted(
                lambda: prompts.number("Width in bits", data_width),
                lambda width: adding(width=width),
            )
        # A fields register without its fields is rejected, so the access is
        # checked on a register without fields.
        access_type = RegisterType.DEFAULT.value if is_fields else register["type"]
        register["sw"], register["hw"] = self._ask_until_accepted(
            self._ask_access,
            lambda access: adding(sw=access[0], hw=access[1], type=access_type),
        )
        if is_fields:
            register["fields"] = self._ask_fields(
                register, lambda fields: adding(fields=fields)
            )
        else:
            register["reset"] = self._ask_until_accepted(
                lambda: hex(prompts.number("Reset value", "0x0")),
                lambda reset: adding(reset=reset),
            )
        register["description"] = prompts.text("Description", "")
        if self._apply(adding()) and prompts.yes(
            f"Set more properties of {register['name']}, such as onwrite?", False
        ):
            self._edit_register_at(len(self._registers()) - 1)

    def _ask_access(self) -> Tuple[str, str]:
        return (
            self._choose_value("sw", "Software access (sw)", "rw"),
            self._choose_value("hw", "Hardware access (hw)", "r"),
        )

    def _ask_until_accepted(
        self,
        ask: Callable[[], Any],
        operations_for: Callable[[Any], List[Operation]],
    ) -> Any:
        """Ask until bust accepts the operations made from the answer."""
        while True:
            answer = ask()
            try:
                self.document.check_operations(operations_for(answer))
                return answer
            except EditRejected as error:
                self.show(str(error))

    def _choose_value(self, key: str, prompt: str, default: str) -> str:
        values = _SCHEMA["register"]["properties"][key]["enum"]
        return str(values[self.prompts.choose(prompt, values, values.index(default))])

    def _ask_fields(
        self,
        access: Dict[str, Any],
        operations_for: Callable[[List[Dict[str, Any]]], List[Operation]],
    ) -> List[Dict[str, Any]]:
        """Ask for one field or more of a register with these access keys.

        Args:
            access: The register's access keys, which the fields inherit.
            operations_for: The operations that give the register these fields.
        """
        fields: List[Dict[str, Any]] = []
        while True:
            next_bit = (
                fields[-1]["position"] + fields[-1].get("width", 1) if fields else 0
            )
            field = self._ask_field(
                access,
                [f["name"] for f in fields],
                next_bit,
                lambda field: operations_for(fields + [field]),
            )
            fields.append(field)
            if not self.prompts.yes("Add another field?", False):
                return fields

    def _ask_field(
        self,
        access: Dict[str, Any],
        taken: List[str],
        next_bit: int,
        operations_for: Callable[[Dict[str, Any]], List[Operation]],
    ) -> Dict[str, Any]:
        """Ask for a field, checking each answer with the operations that add
        it. The field gets sw and hw only where they differ from the
        register's `access`."""
        prompts = self.prompts
        field: Dict[str, Any] = {"name": prompts.identifier("Field name", taken)}

        def ask_checked(ask: Callable[[], Any], key: str) -> Any:
            return self._ask_until_accepted(
                ask, lambda answer: operations_for({**field, key: answer})
            )

        types = FieldType.valid_values()
        field["type"] = types[
            prompts.choose("Field type", types, types.index(FieldType.BIT.value))
        ]
        field["position"] = ask_checked(
            lambda: prompts.number("Lowest bit", str(next_bit)), "position"
        )
        if field["type"] == FieldType.VECTOR.value:
            field["width"] = ask_checked(
                lambda: prompts.number("Width in bits", "2"), "width"
            )
        field.update(
            self._ask_until_accepted(
                lambda: self._ask_field_access(access),
                lambda keys: operations_for({**field, **keys}),
            )
        )
        field["reset"] = ask_checked(
            lambda: hex(prompts.number("Reset value", "0x0")), "reset"
        )
        field["description"] = prompts.text("Description", "")
        return field

    def _ask_field_access(self, access: Dict[str, Any]) -> Dict[str, str]:
        """The field's sw and hw, where they differ from the register's."""
        keys = {}
        for key, prompt in (
            ("sw", "Software access (sw)"),
            ("hw", "Hardware access (hw)"),
        ):
            inherited = access.get(
                key, _SCHEMA["register"]["properties"][key]["default"]
            )
            value = self._choose_value(key, f"{prompt} of the field", inherited)
            if value != inherited:
                keys[key] = value
        return keys

    def edit_register(self) -> None:
        """Change any key of a register, or its fields."""
        index = self._pick_register()
        if index is not None:
            self._edit_register_at(index)

    def _edit_register_at(self, index: int) -> None:
        while True:
            register = self._registers()[index]
            data = self._data["module"]["register"][index]
            keys = ["name", "description", "address", "type"]
            if register.type == RegisterType.VECTOR:
                keys.append("width")
            if register.type != RegisterType.FIELDS:
                keys.append("reset")
            keys += INHERITABLE_ACCESS
            labels = [
                _row(key, self._register_value(index, key), key in data) for key in keys
            ]
            extra = ["Fields"] if register.type == RegisterType.FIELDS else []
            self.show("")
            self.show(f"Register {register.name} at {hex(register.address)}")
            choice = self.prompts.choose("Change", labels + extra + ["Done"])
            if choice == len(labels) + len(extra):
                return
            if choice == len(labels):
                self._edit_fields(index)
            elif keys[choice] == "type":
                self._change_register_type(index)
            else:
                self._edit_key(_register_path(index), "register", keys[choice], data)

    def _register_value(self, index: int, key: str) -> str:
        register = self._registers()[index]
        if key in INHERITABLE_ACCESS:
            default = _SCHEMA["register"]["properties"][key].get("default")
            return shown(register.access_defaults.get(key, default))
        if key == "address":
            return hex(register.address)
        return shown(getattr(register, key))

    def _edit_key(
        self, base: str, definition: str, key: str, data: Dict[str, Any]
    ) -> None:
        """Ask for a new value of `key` in the object at `base`, and apply it."""
        schema = _SCHEMA[definition]["properties"][key]
        self.show(schema["description"])
        path = base + join_pointer(key)
        remove = [{"op": "remove", "path": path}] if key in data else []
        if "enum" in schema:
            options = list(schema["enum"]) + ["not set"]
            current = options.index(data.get(key, "not set"))
            choice = self.prompts.choose(f"New {key}", options, current)
            value: Any = options[choice]
            if value == "not set":
                self._apply(remove)
                return
        elif "boolean" in schema.get("type", ()):
            options = ["true", "false", "not set"]
            current = [True, False, None].index(data.get(key))
            choice = self.prompts.choose(f"New {key}", options, current)
            if choice == 2:
                self._apply(remove)
                return
            value = choice == 0
        else:
            answer = self.prompts.text(
                f"New {key} (Enter keeps it, {_UNSET} removes it)",
                None if key not in data else str(data[key]),
            )
            if answer == _UNSET:
                self._apply(remove)
                return
            if answer == "":
                return
            if "anyOf" in schema:
                try:
                    value = _number_value(key, parse_number(answer, key))
                except FormatError as error:
                    self.show(str(error))
                    return
            else:
                value = answer
        self._apply([{"op": "add", "path": path, "value": value}])

    def _change_register_type(self, index: int) -> None:
        data = self._data["module"]["register"][index]
        old = self._registers()[index].type.value
        types = RegisterType.valid_values()
        new = types[self.prompts.choose("New type", types, types.index(old))]
        if new == old:
            return
        path = _register_path(index)
        operations: List[Operation] = [
            {"op": "add", "path": path + "/type", "value": new}
        ]
        is_fields = new == RegisterType.FIELDS.value
        unused = ["reset"] if is_fields else ["fields"]
        if new != RegisterType.VECTOR.value:
            unused.append("width")
        operations += [
            {"op": "remove", "path": f"{path}/{key}"} for key in unused if key in data
        ]
        if is_fields:
            fields = self._ask_fields(
                self._registers()[index].access_defaults,
                lambda fields: operations
                + [{"op": "add", "path": path + "/fields", "value": fields}],
            )
            operations.append({"op": "add", "path": path + "/fields", "value": fields})
        else:
            if old == RegisterType.FIELDS.value and not self.prompts.yes(
                f"Remove the fields of {data['name']}?", False
            ):
                return
            if new == RegisterType.VECTOR.value:
                width = self.prompts.number(
                    "Width in bits", str(self.document.module.data_width)
                )
                operations.append(
                    {"op": "add", "path": path + "/width", "value": width}
                )
            reset = data.get("reset", "0x0")
            operations.append({"op": "add", "path": path + "/reset", "value": reset})
        self._apply(operations)

    def _edit_fields(self, index: int) -> None:
        actions = ["Add a field", "Edit a field", "Remove a field", "Done"]
        while True:
            self._list_fields(index)
            choice = self.prompts.choose("Fields", actions)
            if choice == 0:
                self._add_field(index)
            elif choice == 1:
                field = self._pick_field(index)
                if field is not None:
                    self._edit_field_at(index, field)
            elif choice == 2:
                self._remove_field(index)
            else:
                return

    def _list_fields(self, index: int) -> None:
        rows = [
            (
                number,
                field.name,
                field.get_pos_str(),
                field.sw.value,
                field.hw.value,
                field.reset,
                shorten(field.description),
            )
            for number, field in enumerate(self._registers()[index].fields, start=1)
        ]
        headers = ("#", "Name", "Bits", "sw", "hw", "Reset", "Description")
        self.show(table(headers, rows))

    def _pick_field(self, index: int) -> Optional[int]:
        names = [field.name for field in self._registers()[index].fields]
        return self._pick("Field", names)

    def _add_field(self, index: int) -> None:
        register = self._registers()[index]
        field = self._ask_field(
            register.access_defaults,
            [f.name for f in register.fields],
            register.get_next_pos_low(),
            lambda field: [
                {"op": "add", "path": _field_path(index, "-"), "value": field}
            ],
        )
        self._apply([{"op": "add", "path": _field_path(index, "-"), "value": field}])

    def _remove_field(self, index: int) -> None:
        field = self._pick_field(index)
        if field is None:
            return
        name = self._registers()[index].fields[field].name
        if self.prompts.yes(f"Remove field {name}?", False):
            self._apply([{"op": "remove", "path": _field_path(index, field)}])

    def _edit_field_at(self, index: int, number: int) -> None:
        while True:
            field = self._registers()[index].fields[number]
            data = self._data["module"]["register"][index]["fields"][number]
            keys = ["name", "description", "type"]
            if field.type == FieldType.VECTOR:
                keys.append("width")
            keys += ["position", "reset", *INHERITABLE_ACCESS]
            labels = [
                _row(key, shown(getattr(field, _ATTRIBUTES.get(key, key))), key in data)
                for key in keys
            ]
            self.show("")
            self.show(f"Field {field.name} of register {self._registers()[index].name}")
            choice = self.prompts.choose(
                "Change", labels + ["Enumerated values", "Done"]
            )
            if choice == len(labels) + 1:
                return
            if choice == len(labels):
                self._edit_enums(index, number)
            else:
                self._edit_key(_field_path(index, number), "field", keys[choice], data)

    def _edit_enums(self, index: int, number: int) -> None:
        path = _field_path(index, number, "enums")
        actions = ["Add a value", "Edit a value", "Remove a value", "Done"]
        while True:
            enums = self._data["module"]["register"][index]["fields"][number].get(
                "enums", []
            )
            rows = [(i, e["name"], e["value"]) for i, e in enumerate(enums, start=1)]
            self.show(table(("#", "Name", "Value"), rows))
            choice = self.prompts.choose("Enumerated values", actions)
            if choice == 0:
                name = self.prompts.identifier("Name", [e["name"] for e in enums])
                value = self.prompts.number("Value", str(len(enums)))
                entry = {"name": name, "value": value}
                if enums:
                    self._apply([{"op": "add", "path": path + "/-", "value": entry}])
                else:
                    self._apply([{"op": "add", "path": path, "value": [entry]}])
            elif choice == 1:
                self._edit_enum(path, enums)
            elif choice == 2:
                remove = self._pick("Value", [e["name"] for e in enums])
                if remove is not None and len(enums) == 1:
                    self._apply([{"op": "remove", "path": path}])
                elif remove is not None:
                    self._apply([{"op": "remove", "path": f"{path}/{remove}"}])
            else:
                return

    def _edit_enum(self, path: str, enums: List[Dict[str, Any]]) -> None:
        number = self._pick("Value", [e["name"] for e in enums])
        if number is None:
            return
        entry = enums[number]
        keys = ["name", "value"]
        labels = [_row(key, str(entry[key]), True) for key in keys]
        key = keys[self.prompts.choose("Change", labels)]
        self._edit_key(f"{path}/{number}", "enum_value", key, entry)

    def remove_register(self) -> None:
        """Remove a register after asking."""
        index = self._pick_register()
        if index is None:
            return
        name = self._registers()[index].name
        if self.prompts.yes(f"Remove register {name}?", False):
            self._apply([{"op": "remove", "path": _register_path(index)}])

    def edit_module(self) -> None:
        """Change the module's name, description, version and addressing, and
        the bus."""
        while True:
            module = self.document.module
            data = self._data
            items = [
                ("module", key, shown(getattr(module, key)), key in data["module"])
                for key in ("name", "description", "version", "byte_addressable")
            ] + [
                ("bus", key, shown(getattr(module.bus, attribute)), True)
                for key, attribute in (
                    ("type", "bus_type"),
                    ("addr_width", "addr_width"),
                    ("data_width", "data_width"),
                )
            ]
            labels = [
                _row(f"{section} {key}", value, is_set)
                for section, key, value, is_set in items
            ]
            self.show("")
            choice = self.prompts.choose("Change", labels + ["Done"])
            if choice == len(labels):
                return
            section, key, _, _ = items[choice]
            self._edit_key(f"/{section}", section, key, data[section])

    def fill_addresses(self) -> None:
        """Write the address bust gives each register without an `address`, so
        that adding registers later cannot move it."""
        registers = self._data["module"]["register"]
        operations = [
            {
                "op": "add",
                "path": _register_path(index, "address"),
                "value": hex(self._registers()[index].address),
            }
            for index, register in enumerate(registers)
            if "address" not in register
        ]
        if not operations:
            self.show("Every register has an address.")
        elif self._apply(operations):
            self.show(f"Gave {len(operations)} registers their address.")

    def save(self) -> bool:
        """Save if the register map changed.

        Returns:
            False if saving failed.
        """
        if not self.document.is_modified:
            self.show("There are no changes to save.")
            return True
        if not self.document.keeps_formatting and not self.prompts.yes(
            f"Saving rewrites {self.path} as plain JSON without comments. Save?",
            False,
        ):
            return False
        try:
            self.document.save(self.path)
        except (FileChanged, FileExistsError) as error:
            self.show(f"Not saved: {error}")
            return False
        self.show(f"Saved {self.path}.")
        return True


def _row(key: str, value: str, is_set: bool) -> str:
    return f"{key:<16} {value}" if is_set else f"{key:<16} {value} (not set)"
