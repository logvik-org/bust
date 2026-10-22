"""The editor's light and dark themes, in the colours of the documentation.

The colours are those of the Furo theme options in docs/conf.py, so the editor
and the documentation on Read the Docs look alike.
"""

from textual.theme import Theme

LIGHT = Theme(
    name="bust-light",
    dark=False,
    primary="#2c6e6a",
    secondary="#4a4d43",
    accent="#2c6e6a",
    foreground="#1c2118",
    background="#f2eee3",
    surface="#e9e3d3",
    panel="#e3ddcb",
    warning="#9a6a1e",
    error="#a8463c",
    success="#4f7d3a",
)

DARK = Theme(
    name="bust-dark",
    dark=True,
    primary="#5fa8a0",
    secondary="#c9c3b6",
    accent="#5fa8a0",
    foreground="#ece8df",
    background="#1f1e1d",
    surface="#2a2725",
    panel="#2f2c2a",
    warning="#d6a24e",
    error="#d9776b",
    success="#7fae63",
)
