"""Compatibility layer: translate the legacy register schema onto the v1
access-mode model.

The legacy schema describes a register with a single `mode` (`rw`/`ro`/`pulse`)
plus `pulse_cycles`/`stall_cycles`. The v1 model describes access per field with
`sw`/`hw` plus side effects and modifiers (see `bust.core.enums`). This module
maps the former onto the latter so existing JSON keeps working while the new
generator consumes a single representation.

Translation is intentionally lossless for `rw`/`ro`. A legacy `pulse` register
maps to a single-cycle pulse (`singlepulse`), which is the only pulse mechanism
v1 supports; a `pulse_cycles` other than 1 cannot be represented and is reported.
"""

import logging
from typing import Dict, List

from bust.core.enums import RegisterMode
from bust.core.field import INHERITABLE_ACCESS

logger = logging.getLogger(__name__)

# Register-level keys that signal the new access-mode schema is in use.
_NEW_SCHEMA_KEYS: List[str] = list(INHERITABLE_ACCESS)


def uses_new_schema(reg: Dict) -> bool:
    """Return True if the register uses the v1 access-mode keys directly."""
    return any(key in reg for key in _NEW_SCHEMA_KEYS)


def register_access_defaults(reg: Dict) -> Dict:
    """Resolve the access-mode defaults a register's fields inherit.

    New-schema registers contribute their access-mode keys verbatim. Legacy
    registers contribute the translation of their `mode`.
    """
    if uses_new_schema(reg):
        return {key: reg[key] for key in _NEW_SCHEMA_KEYS if key in reg}
    return _translate_legacy_mode(reg)


def _translate_legacy_mode(reg: Dict) -> Dict:
    """Map a legacy `mode` (defaulting to rw) onto sw/hw access defaults."""
    mode = RegisterMode.from_string(reg.get("mode", RegisterMode.RW.value))

    if mode is RegisterMode.RW:
        return {"sw": "rw", "hw": "r"}
    if mode is RegisterMode.RO:
        return {"sw": "ro", "hw": "w"}

    # PULSE: software writes a value that reaches hardware as a pulse, then
    # self-clears. v1 expresses this as a single-cycle pulse.
    pulse_cycles = reg.get("pulse_cycles", 1)
    if pulse_cycles != 1:
        logger.warning(
            "Register '%s': legacy pulse_cycles=%s collapses to a single-cycle "
            "pulse under the v1 access model (singlepulse).",
            reg.get("name", "<unknown>"),
            pulse_cycles,
        )
    return {"sw": "wo", "hw": "r", "singlepulse": True}
