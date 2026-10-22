"""bust FILE --migrate: move a bust 0.14 register map and top level to bust 1.0.

The register map is changed to the bust 1.0 form without moving a register,
and each register's `mode` becomes the access keys it stands for.
A 0.14 <module>.vhd keeps its entity and the user's logic. Its _pif instance
becomes an instance of the bus endpoint, and the 0.14 register records become
to_hw and from_hw.
"""

import logging
import os
import re
import shutil
import sys

from bust.editing.document import RegisterMapDocument
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

    The register map is saved through RegisterMapDocument, so only the values
    that change are rewritten. Each file that changes is kept with the suffix
    .0_14.
    """
    document = RegisterMapDocument.open(json_file)
    old = document.data.get("settings") or {}
    changes, operations = document.legacy_conversion()
    document.apply(operations)
    module = document.module
    settings = Settings(json_file, None)

    # Where the 0.14 settings put the output, and where bust 1.0 puts it.
    new_dir = os.path.expanduser(out_dir or settings.project_path)
    mod_dir = os.path.expanduser(out_dir or old.get("proj_dir") or new_dir)
    if old.get("mod_subdir", True):
        mod_dir = os.path.join(mod_dir, module.name)
    mod_dir = os.path.normpath(mod_dir)
    moved = mod_dir != os.path.normpath(os.path.join(new_dir, module.name))
    top_path = os.path.join(mod_dir, settings.hdl_dir, f"{module.name}.vhd")
    tops = []
    todo = []
    if os.path.isfile(top_path):
        with open(top_path, encoding="utf-8") as fp:
            top = fp.read()
        if is_legacy_top(top):
            new_top, todo = migrate_top(top, module)
            tops.append((top_path, new_top))
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

    if document.is_modified:
        shutil.copyfile(json_file, json_file + ".0_14")
        document.save(json_file)
    for path, text in tops:
        shutil.copyfile(path, path + ".0_14")
        with open(path, "w", encoding="utf-8") as fp:
            fp.write(text)
    for line in todo:
        logger.warning(f"Change by hand in {top_path}, {line}")
    option = ""
    if moved and os.path.basename(mod_dir) == module.name:
        option = f" -o {os.path.dirname(mod_dir) or '.'}"
    elif moved:
        logger.warning(
            f"bust now writes into <-o DIR>/{module.name}/. Move {mod_dir} to "
            f"a directory named {module.name}."
        )
    logger.info(
        f"Migrated. The old files end in .0_14. Now run bust {json_file}{option}."
    )
