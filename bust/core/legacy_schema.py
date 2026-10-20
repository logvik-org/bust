"""Compatibility layer: translate the legacy register schema onto the bust 1.0
access-mode model.

The legacy schema describes a register with a single `mode` (`rw`/`ro`/`pulse`)
plus `pulse_cycles`/`stall_cycles`. The 1.0 model describes access per field with
`sw`/`hw` plus side effects and modifiers (see `bust.core.enums`). This module
maps the former onto the latter so existing JSON keeps working while the new
generator consumes a single representation.

Translation is intentionally lossless for `rw`/`ro`. A legacy `pulse` register
maps to `singlepulse`, the only pulse mechanism bust 1.0 supports: the written
value reaches hardware for one clock cycle and the field then returns to its
reset value. A `pulse_cycles` other than 1 and a `stall_cycles` other than 0
cannot be represented, so they are rejected rather than silently changed.
"""

from typing import Dict, List

from bust.core.enums import RegisterMode
from bust.core.field import INHERITABLE_ACCESS
from bust.exceptions import InvalidRegisterFormat

# Register-level keys that signal the new access-mode schema is in use.
_NEW_SCHEMA_KEYS: List[str] = list(INHERITABLE_ACCESS)


def uses_new_schema(reg: Dict) -> bool:
    """Return True if the register uses the bust 1.0 access-mode keys directly."""
    return any(key in reg for key in _NEW_SCHEMA_KEYS)


def reject_unsupported_timing(reg: Dict) -> None:
    """Reject legacy `pulse_cycles`/`stall_cycles` values bust 1.0 cannot honour.

    `pulse_cycles: 1` and `stall_cycles: 0` describe what every register already
    does, so they are accepted as no-ops.

    Raises:
        InvalidRegisterFormat: If either key asks for other timing.
    """
    name = reg.get("name", "<unknown>")
    pulse_cycles = reg.get("pulse_cycles", 1)
    if pulse_cycles != 1:
        raise InvalidRegisterFormat(
            f"Register '{name}': pulse_cycles={pulse_cycles} is not supported in "
            "bust 1.0. A pulse register drives the written value for one clock "
            "cycle and then returns to its reset value. Remove pulse_cycles. "
            "To reach logic on another clock, see "
            "https://bust.readthedocs.io/en/latest/access-modes.html#pulses-into-another-clock-domain"
        )
    if reg.get("stall_cycles", 0) != 0:
        raise InvalidRegisterFormat(
            f"Register '{name}': stall_cycles is not supported in bust 1.0, "
            "because registers live in the generated register file and always "
            "answer in one cycle. Remove stall_cycles."
        )


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

    # PULSE: software writes a value that reaches hardware for one cycle, then
    # the field returns to its reset value.
    return {"sw": "wo", "hw": "r", "singlepulse": True}
