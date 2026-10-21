"""bust FILE --migrate: move a bust 0.14 register map and top level to bust 1.0.

The register map is rewritten in the bust 1.0 form without moving a register.
A 0.14 <module>.vhd keeps its entity and the user's logic. Its _pif instance
becomes an instance of the bus endpoint, and the 0.14 register records become
to_hw and from_hw.
"""

import json
import logging
import os
import re
import shutil
import sys

from bust.core.bus import Bus
from bust.core.enums import current_type_name
from bust.core.legacy_schema import reject_unsupported_timing
from bust.core.module import Module
from bust.exceptions import FormatError
from bust.interaction import ConsoleInteractionHandler
from bust.jinja_utils.environment import render_template
from bust.settings import Settings

logger = logging.getLogger(__name__)

_USER_MARKER = re.compile(r"^\s*-- User \w+ (Start|End)\s*$", re.MULTILINE)
_PIF_INSTANCE = re.compile(r"\bentity\s+work\.\w+_(ipb|axi)_pif\b", re.IGNORECASE)


def is_legacy_top(text):
    """True for a bust 0.14 top level: user regions and a _pif instance."""
    return bool(_USER_MARKER.search(text) and _PIF_INSTANCE.search(text))


def migrate_register_map(cfg):
    """Rewrite a bust 0.14 register map in place and return the changes made."""
    changes = []
    for section, keys in (
        ("settings", Settings.IGNORED_KEYS),
        ("bus", Bus.IGNORED_KEYS),
    ):
        for key in keys:
            if cfg.get(section, {}).pop(key, None) is not None:
                changes.append(f"removed {section}.{key}")
    module = cfg["module"]
    if module.get("byte_addressable") in ("True", "False"):
        module["byte_addressable"] = module["byte_addressable"] == "True"
        changes.append("byte_addressable is now a boolean")
    for reg in module["register"]:
        reject_unsupported_timing(reg)
        for key in ("pulse_cycles", "stall_cycles"):
            if reg.pop(key, None) is not None:
                changes.append(f"removed {key} from register {reg['name']}")
        for item in [reg, *reg.get("fields", [])]:
            if current_type_name(item.get("type")) != item.get("type"):
                item["type"] = current_type_name(item["type"])
                changes.append(f"{item['name']}: type is now {item['type']}")
            for key in ("address", "reset"):
                value = item.get(key)
                # bust 0.14 read these as hexadecimal, bust 1.0 reads them as
                # decimal. 0 to 9 mean the same in both.
                if (
                    isinstance(value, str)
                    and re.fullmatch(r"[0-9a-fA-F]+", value)
                    and not re.fullmatch(r"[0-9]", value)
                ):
                    item[key] = "0x" + value
                    changes.append(
                        f'{item["name"]}: {key} "{value}" is now "0x{value}"'
                    )
    return changes


def migrate_top(text, module):
    """Connect a bust 0.14 top level to the bust 1.0 endpoint.

    Returns:
        The new text and the lines that still need a change by hand.
    """
    name = module.name
    kind = {"ipbus": "ipb", "axi": "axi"}.get(module.bus.bus_type)
    context = {"module": module, "bus": module.bus, "prefix": kind}
    steps = [
        (
            rf"^[ \t]*\w+[ \t]*:[ \t]*entity[ \t]+work\.{name}_{kind}_pif\b"
            r".*?^[ \t]*\);[ \t]*\n",
            render_template("vhdl/migrate/instance.j2", context),
        ),
        (
            r"(?:^[ \t]*-- Register Signals[ \t]*\n)?"
            rf"(?:^[ \t]*signal[ \t]+{kind}_(?:rw|ro|pulse)_regs\b[^;]*;[ \t]*\n)+",
            render_template("vhdl/migrate/declarations.j2", context),
        ),
        (rf"\bwork\.{name}_pif_pkg\b", f"work.{name}_regfile_pkg"),
    ]
    for pattern, replacement in steps:
        text, count = re.subn(
            pattern,
            lambda _: replacement,
            text,
            count=1,
            flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
        )
        if count == 0:
            raise FormatError(
                f"{name}.vhd does not look like a bust 0.14 {kind} top level. "
                "Connect it by hand as described in Upgrading from 0.14."
            )
    text = re.sub(rf"\b{kind}_(rw|pulse)_regs\.", "to_hw.", text, flags=re.I)
    text = re.sub(rf"\b{kind}_ro_regs\.", "from_hw.", text, flags=re.I)
    leftover = re.compile(rf"\b({kind}_\w+_regs|[tc]_{name}_\w+_regs)\b", re.I)
    todo = [
        f"line {number}: {line.strip()}"
        for number, line in enumerate(text.splitlines(), start=1)
        if leftover.search(line)
    ]
    return text, todo


def migrate(json_file, out_dir, force):
    """Migrate a register map and its top level, asking first unless `force`.

    Each file that changes is kept with the suffix .0_14.
    """
    with open(json_file, encoding="utf-8") as fp:
        cfg = json.load(fp)
    changes = migrate_register_map(cfg)
    settings = Settings(json_file, cfg.get("settings"))
    module = Module(cfg["module"], Bus(cfg["bus"]), settings)

    mod_dir = os.path.expanduser(out_dir or settings.project_path)
    if settings.mod_subdir:
        mod_dir = os.path.join(mod_dir, module.name)
    top_path = os.path.join(mod_dir, settings.hdl_dir, f"{module.name}.vhd")
    files = [(json_file, json.dumps(cfg, indent=4) + "\n")] if changes else []
    todo = []
    if os.path.isfile(top_path):
        with open(top_path, encoding="utf-8") as fp:
            top = fp.read()
        if is_legacy_top(top):
            new_top, todo = migrate_top(top, module)
            files.append((top_path, new_top))
            endpoint = f"{module.name}_{module.bus.endpoint_suffix}"
            changes.append(f"{top_path}: connected to {endpoint}")

    if not changes:
        logger.info("Nothing to migrate.")
        return
    logger.info(f"Migrating {json_file}:")
    for change in changes:
        logger.info(f"  - {change}")
    if not force:
        if not sys.stdin.isatty():
            raise FormatError("No terminal to ask. Run bust with --migrate -f.")
        if ConsoleInteractionHandler()("Migrate? (y/N):").upper() != "Y":
            return

    for path, text in files:
        shutil.copyfile(path, path + ".0_14")
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(text)
    for line in todo:
        logger.warning(f"Change by hand in {top_path}, {line}")
    logger.info(f"Migrated. The old files end in .0_14. Now run bust {json_file}.")
