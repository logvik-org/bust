"""What the editor shows and the changes it makes, without the user interface.

EditSession turns the editor's actions into JSON Patch operations on a
RegisterMapDocument, and lists the rows the editor shows. Every change goes
through the document, so the editor cannot save a register map bust rejects.
The allowed values and defaults of each key come from the JSON Schema in
bust.schema.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from bust.core.bus import Bus
from bust.core.enums import FieldType, RegisterType
from bust.core.field import INHERITABLE_ACCESS, Field
from bust.core.register import Register
from bust.editing.document import Operation, RegisterMapDocument
from bust.editing.json_source import join_pointer, split_pointer
from bust.exceptions import FormatError
from bust.schema import register_map_schema
from bust.validation.config_validator import parse_number
from bust.validation.vhdl_validator import is_unique, is_valid_VHDL

SCHEMA = register_map_schema()["$defs"]
# Written as "0x..." strings, the form bust's own files use.
_HEX_KEYS = ("address", "reset")
# Model attributes named differently from their key.
_ATTRIBUTES = {"position": "pos_low"}
# Keys a register map needs, which the editor never removes.
_REQUIRED = ("name", "type", "addr_width", "data_width")


def register_path(index: Union[int, str], *keys: Any) -> str:
    """The JSON Pointer of register `index`, or of a key in it."""
    return join_pointer("module", "register", index, *keys)


def field_path(register: int, field: Union[int, str], *keys: Any) -> str:
    """The JSON Pointer of a field of register `register`, or of a key in it."""
    return register_path(register, "fields", field, *keys)


def shown(value: Any) -> str:
    """A value as the editor shows it."""
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, bool):
        return str(value).lower()
    return "" if value is None else str(value)


def number_value(key: str, text: str) -> Any:
    """The value to write for a number typed as `text`.

    Raises:
        FormatError: If `text` is not a number.
    """
    number = parse_number(text.strip(), key)
    return hex(number) if key in _HEX_KEYS else number


def check_identifier(name: str, taken: Sequence[str]) -> None:
    """Raise with bust's message if `name` is not a new VHDL identifier."""
    is_valid_VHDL(name)
    is_unique(name, list(taken))


@dataclass
class Property:
    """One key of a register, field or the module, as the editor lists it.

    Attributes:
        definition: The schema definition the key belongs to, such as
            "register".
        path: The JSON Pointer of the object that holds the key.
        key: The key.
        value: The value bust uses, as shown.
        is_set: True if the file sets the key.
        current: The value in the file, or None.
    """

    definition: str
    path: str
    key: str
    value: str
    is_set: bool
    current: Any

    @property
    def schema(self) -> Dict[str, Any]:
        schema: Dict[str, Any] = SCHEMA[self.definition]["properties"][self.key]
        return schema

    @property
    def description(self) -> str:
        return str(self.schema.get("description", ""))

    @property
    def choices(self) -> Optional[List[str]]:
        """The values to choose from, or None for a key typed as text."""
        if "enum" in self.schema:
            return [str(value) for value in self.schema["enum"]]
        if "boolean" in self.schema.get("type", ()):
            return ["true", "false"]
        return None

    @property
    def removable(self) -> bool:
        return self.is_set and self.key not in _REQUIRED

    @property
    def label(self) -> str:
        if self.definition in ("module", "bus"):
            return f"{self.definition} {self.key}"
        return self.key


class EditSession:
    """The register map one editor works on, and the file it saves to."""

    def __init__(self, document: RegisterMapDocument, path: str) -> None:
        self.document = document
        self.path = path

    @staticmethod
    def new_document(
        bus_type: str,
        addr_width: str,
        data_width: str,
        module: Dict[str, Any],
    ) -> RegisterMapDocument:
        """Start a register map with no registers.

        Raises:
            FormatError: If bust rejects the bus or the module name.
            EditRejected: If bust rejects the module.
        """
        config = Bus.BUS_CONFIG[bus_type]
        bus = {
            "type": bus_type,
            "addr_width": parse_number(addr_width.strip(), "The address width"),
            "data_width": config["fixed_data_width"]
            or parse_number(data_width.strip(), "The data width"),
        }
        Bus(bus)
        check_identifier(module["name"], [])
        return RegisterMapDocument.new(bus, module)

    @property
    def data(self) -> Any:
        return self.document.data

    @property
    def registers(self) -> List[Register]:
        return self.document.module.registers

    def status(self) -> str:
        """One line on the module, the bus and whether there are changes."""
        module = self.document.module
        bus = module.bus
        saved = "unsaved changes" if self.document.is_modified else "saved"
        count = len(module.registers)
        return (
            f"module {module.name}  ·  {bus.bus_type}  ·  "
            f"{bus.addr_width}-bit addresses  ·  {bus.data_width}-bit data  ·  "
            f"{count} register{'' if count == 1 else 's'}  ·  {saved}"
        )

    # Rows the editor lists.

    def register_rows(self) -> List[Tuple[str, ...]]:
        return [
            (
                reg.name,
                hex(reg.address),
                reg.type.value,
                str(reg.width) if reg.type != RegisterType.FIELDS else "",
                reg.sw.value,
                reg.hw.value,
                reg.reset if reg.type != RegisterType.FIELDS else "",
                reg.description,
            )
            for reg in self.registers
        ]

    def field_rows(self, index: int) -> List[Tuple[str, ...]]:
        return [
            (
                field.name,
                field.get_pos_str(),
                field.type.value,
                field.sw.value,
                field.hw.value,
                field.reset,
                field.description,
            )
            for field in self.registers[index].fields
        ]

    def enum_rows(self, index: int, number: int) -> List[Tuple[str, str]]:
        return [(str(e["name"]), str(e["value"])) for e in self._enums(index, number)]

    def register_properties(self, index: int) -> List[Property]:
        register = self.registers[index]
        data = self.data["module"]["register"][index]
        keys = ["name", "description", "address", "type"]
        if register.type == RegisterType.VECTOR:
            keys.append("width")
        if register.type != RegisterType.FIELDS and not register.type.is_constant:
            keys.append("reset")
        # bust sets the access and the value of a hash or version register.
        if not register.type.is_constant:
            keys += INHERITABLE_ACCESS
        rows = []
        for key in keys:
            if key in INHERITABLE_ACCESS:
                default = SCHEMA["register"]["properties"][key].get("default")
                value = shown(register.access_defaults.get(key, default)) or "none"
            elif key == "address":
                value = hex(register.address)
            else:
                value = shown(getattr(register, key))
            rows.append(
                Property(
                    "register",
                    register_path(index),
                    key,
                    value,
                    key in data,
                    data.get(key),
                )
            )
        return rows

    def field_properties(self, index: int, number: int) -> List[Property]:
        field = self.registers[index].fields[number]
        data = self.data["module"]["register"][index]["fields"][number]
        keys = ["name", "description", "type"]
        if field.type == FieldType.VECTOR:
            keys.append("width")
        keys += ["position", "reset", *INHERITABLE_ACCESS]
        path = field_path(index, number)
        return [
            Property(
                "field",
                path,
                key,
                shown(getattr(field, _ATTRIBUTES.get(key, key)))
                or ("none" if key in INHERITABLE_ACCESS else ""),
                key in data,
                data.get(key),
            )
            for key in keys
        ]

    def module_properties(self) -> List[Property]:
        module = self.document.module
        data = self.data
        rows = [
            Property(
                "module",
                "/module",
                key,
                shown(getattr(module, key)),
                key in data["module"],
                data["module"].get(key),
            )
            for key in ("name", "description", "version", "byte_addressable")
        ]
        rows += [
            Property(
                "bus",
                "/bus",
                key,
                shown(getattr(module.bus, attribute)),
                True,
                data["bus"].get(key),
            )
            for key, attribute in (
                ("type", "bus_type"),
                ("addr_width", "addr_width"),
                ("data_width", "data_width"),
            )
        ]
        return rows

    # Changes. Each returns the operations, which the caller applies.

    def set_operations(self, prop: Property, answer: Optional[str]) -> List[Operation]:
        """The operations that give `prop` the value `answer`, or remove it from
        the file for None.

        Raises:
            FormatError: If `answer` is not a number for a number key.
        """
        path = prop.path + join_pointer(prop.key)
        if answer is None:
            return [{"op": "remove", "path": path}] if prop.is_set else []
        value: Any = answer
        if "anyOf" in prop.schema:
            value = number_value(prop.key, answer)
        elif prop.choices == ["true", "false"]:
            value = answer == "true"
        operations: List[Operation] = [{"op": "add", "path": path, "value": value}]
        if prop.definition == "field" and prop.key == "type":
            # A width is meaningless on a bit field.
            data = self._at(prop.path)
            if answer == FieldType.BIT.value and "width" in data:
                operations.append({"op": "remove", "path": prop.path + "/width"})
        return operations

    def register_type_operations(
        self, index: int, new: str, first_field: Optional[Dict[str, Any]] = None
    ) -> List[Operation]:
        """The operations that change the type of register `index` to `new`.

        A `fields` register needs `first_field`. The keys the new type does not
        use, such as the width of a former vector or the access keys of a hash
        register, are removed.
        """
        data = self.data["module"]["register"][index]
        old = self.registers[index].type.value
        if new == old:
            return []
        path = register_path(index)
        operations: List[Operation] = [
            {"op": "add", "path": path + "/type", "value": new}
        ]
        unused = ["reset"] if new == RegisterType.FIELDS.value else ["fields"]
        if new != RegisterType.VECTOR.value:
            unused.append("width")
        is_constant = RegisterType(new).is_constant
        if is_constant:
            unused += ["reset", "mode", *INHERITABLE_ACCESS]
        operations += [
            {"op": "remove", "path": f"{path}/{key}"} for key in unused if key in data
        ]
        if is_constant:
            return operations
        if new == RegisterType.FIELDS.value:
            operations.append(
                {"op": "add", "path": path + "/fields", "value": [first_field]}
            )
            return operations
        if new == RegisterType.VECTOR.value:
            width = self.document.module.data_width
            operations.append({"op": "add", "path": path + "/width", "value": width})
        reset = data.get("reset", "0x0")
        operations.append({"op": "add", "path": path + "/reset", "value": reset})
        return operations

    def add_register_operations(self, register: Dict[str, Any]) -> List[Operation]:
        return [{"op": "add", "path": register_path("-"), "value": register}]

    def add_field_operations(
        self, index: int, field: Dict[str, Any]
    ) -> List[Operation]:
        return [{"op": "add", "path": field_path(index, "-"), "value": field}]

    def remove_register_operations(self, index: int) -> List[Operation]:
        return [{"op": "remove", "path": register_path(index)}]

    def remove_field_operations(self, index: int, number: int) -> List[Operation]:
        return [{"op": "remove", "path": field_path(index, number)}]

    def enum_operations(
        self,
        index: int,
        number: int,
        entry: Optional[Dict[str, Any]],
        replace: Optional[int] = None,
    ) -> List[Operation]:
        """Add `entry` to the enumerated values of a field, replace entry
        `replace` with it, or remove entry `replace` for an `entry` of None.
        The `enums` key goes when its last value does."""
        path = field_path(index, number, "enums")
        enums = self._enums(index, number)
        if entry is None and replace is not None:
            if len(enums) == 1:
                return [{"op": "remove", "path": path}]
            return [{"op": "remove", "path": f"{path}/{replace}"}]
        if replace is not None:
            return [{"op": "replace", "path": f"{path}/{replace}", "value": entry}]
        if not enums:
            return [{"op": "add", "path": path, "value": [entry]}]
        return [{"op": "add", "path": path + "/-", "value": entry}]

    def fill_address_operations(self) -> List[Operation]:
        """Write the address bust gives each register without an `address`, so
        that adding registers later cannot move it."""
        return [
            {
                "op": "add",
                "path": register_path(index, "address"),
                "value": hex(self.registers[index].address),
            }
            for index, register in enumerate(self.data["module"]["register"])
            if "address" not in register
        ]

    # Defaults for new registers and fields.

    def next_address(self) -> str:
        return hex(self.document.next_free_address())

    def next_bit(self, index: int) -> int:
        return self.registers[index].get_next_pos_low()

    def access_of(self, index: int) -> Dict[str, Any]:
        """The access keys the fields of register `index` inherit."""
        return dict(self.registers[index].access_defaults)

    def field_of(self, index: int, number: int) -> Field:
        return self.registers[index].fields[number]

    def _enums(self, index: int, number: int) -> List[Dict[str, Any]]:
        field = self.data["module"]["register"][index]["fields"][number]
        return list(field.get("enums", []))

    def _at(self, path: str) -> Any:
        data = self.data
        for part in split_pointer(path):
            data = data[int(part)] if isinstance(data, list) else data[part]
        return data


def inherited_access(access: Dict[str, Any], key: str) -> str:
    """The value of `key`, sw or hw, a field inherits from `access`."""
    return str(access.get(key, SCHEMA["register"]["properties"][key]["default"]))


def access_choices(key: str) -> List[str]:
    return [str(value) for value in SCHEMA["register"]["properties"][key]["enum"]]


__all__ = [
    "EditSession",
    "FormatError",
    "Property",
    "access_choices",
    "check_identifier",
    "field_path",
    "inherited_access",
    "number_value",
    "register_path",
    "shown",
]
