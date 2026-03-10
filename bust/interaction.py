"""Interaction handler interface and implementations for bust.

This module provides the InteractionHandler protocol for abstracting user
interaction, enabling both interactive console use and automated/headless
operation without requiring input() calls in utility functions.
"""

from abc import ABC, abstractmethod


class InteractionHandler(ABC):
    """Abstract base class that acts as a drop-in replacement for input().

    Implement ``__call__`` to control how bust handles any situation that
    requires a prompt response.  This decouples utility functions from
    console I/O, making them unit-testable and suitable for automated usage.
    """

    @abstractmethod
    def __call__(self, prompt: str) -> str:
        """Prompt the user and return their response.

        Args:
            prompt: The message shown to the user (same as the argument to
                the built-in ``input()``).

        Returns:
            The user's response as a string.
        """


class ConsoleInteractionHandler(InteractionHandler):
    """InteractionHandler that reads responses from stdin via input().

    This is the default handler used in interactive CLI sessions.
    """

    def __call__(self, prompt: str) -> str:
        """Delegate to the built-in input().

        Args:
            prompt: Message shown to the user.

        Returns:
            The string the user typed.
        """
        return input(prompt)


class AutomatedInteractionHandler(InteractionHandler):
    """InteractionHandler for automated/headless usage without user prompts.

    Every call returns the same pre-configured *default* string, making this
    handler suitable for scripted pipelines, CI environments, and unit tests.
    """

    def __init__(self, default: str = "") -> None:
        """Initialise with a fixed response value.

        Args:
            default: The string to return for every prompt (default: ``""``).
        """
        self._default = default

    def __call__(self, prompt: str) -> str:
        """Return the configured default without prompting.

        Args:
            prompt: Ignored; present for interface compatibility.

        Returns:
            The default value set at construction time.
        """
        return self._default
