"""Terminal questions and tables for the editor."""

from typing import Any, Callable, Optional, Sequence

from bust.exceptions import FormatError
from bust.interaction import InteractionHandler
from bust.validation.config_validator import parse_number
from bust.validation.vhdl_validator import is_unique, is_valid_VHDL


class Prompts:
    """Questions answered through an InteractionHandler, asked again until the
    answer is valid."""

    def __init__(self, ask: InteractionHandler, show: Callable[[str], None]):
        self.ask = ask
        self.show = show

    def text(self, prompt: str, default: Optional[str] = None) -> str:
        suffix = f" [{default}]" if default else ""
        answer = self.ask(f"{prompt}{suffix}: ").strip()
        return default if answer == "" and default is not None else answer

    def yes(self, prompt: str, default: bool) -> bool:
        hint = "Y/n" if default else "y/N"
        while True:
            answer = self.ask(f"{prompt} ({hint}): ").strip().lower()
            if answer == "":
                return default
            if answer in ("y", "yes", "n", "no"):
                return answer.startswith("y")
            self.show("Answer y or n.")

    def choose(self, prompt: str, options: Sequence[str], default: int = 0) -> int:
        """The index of the option chosen by its number or its text."""
        for number, option in enumerate(options, start=1):
            self.show(f"  {number}. {option}")
        while True:
            answer = self.ask(f"{prompt} [{default + 1}]: ").strip()
            if answer == "":
                return default
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return int(answer) - 1
            if answer in options:
                return list(options).index(answer)
            self.show(f"Enter a number from 1 to {len(options)}.")

    def number(self, prompt: str, default: Optional[str] = None) -> int:
        while True:
            answer = self.text(prompt, default)
            try:
                return parse_number(answer, "The number")
            except FormatError as error:
                self.show(str(error))

    def identifier(
        self, prompt: str, taken: Sequence[str], default: Optional[str] = None
    ) -> str:
        while True:
            answer = self.text(prompt, default)
            try:
                is_valid_VHDL(answer)
                is_unique(answer, taken)
                return answer
            except Exception as error:
                self.show(str(error))


def table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    cells = [list(map(str, headers))] + [list(map(str, row)) for row in rows]
    widths = [max(len(row[i]) for row in cells) for i in range(len(headers))]
    lines = ["  ".join(c.ljust(w) for c, w in zip(row, widths)) for row in cells]
    return "\n".join(line.rstrip() for line in lines)


def shorten(text: str, length: int = 40) -> str:
    return text if len(text) <= length else text[: length - 3] + "..."


def shown(value: Any) -> str:
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, bool):
        return str(value).lower()
    return "none" if value is None else str(value)
