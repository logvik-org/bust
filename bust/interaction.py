"""Interaction handler interface and implementations for bust.

This module provides the InteractionHandler protocol for abstracting user
interaction, enabling both interactive console use and automated/headless
operation without requiring input() calls in utility functions.
"""

from abc import ABC, abstractmethod


class InteractionHandler(ABC):
    """Abstract base class for handling user interaction prompts.

    Implement this interface to control how bust responds to situations that
    require a decision (e.g., overwriting an existing file). This decouples
    utility functions from console I/O, making them unit-testable and
    suitable for automated usage.
    """

    @abstractmethod
    def confirm_overwrite(self, filepath: str) -> bool:
        """Ask whether an existing file should be overwritten.

        Args:
            filepath: Absolute or relative path to the file in question.

        Returns:
            True if the file should be overwritten, False to skip writing.
        """

    @abstractmethod
    def confirm_preview(self) -> bool:
        """Ask whether the updated content should be previewed before writing.

        Returns:
            True if the content should be printed for review, False to skip.
        """

    @abstractmethod
    def confirm_update(self, filepath: str) -> bool:
        """Ask whether an existing file should be updated.

        Args:
            filepath: Absolute or relative path to the file in question.

        Returns:
            True if the file should be updated, False to abort.
        """


class ConsoleInteractionHandler(InteractionHandler):
    """InteractionHandler that prompts the user via the console.

    This is the default handler used in interactive CLI sessions. All
    decisions are delegated to the user through stdin prompts.
    """

    def confirm_overwrite(self, filepath: str) -> bool:
        """Prompt the user to confirm overwriting an existing file.

        Args:
            filepath: Path to the file that would be overwritten.

        Returns:
            True if the user answers 'y' or 'Y', False otherwise.
        """
        return input(f"Do you want to overwrite {filepath}? (y/N):").upper() == "Y"

    def confirm_preview(self) -> bool:
        """Prompt the user to decide whether to preview the updated content.

        Returns:
            True if the user answers 'y' or 'Y', False otherwise.
        """
        return (
            input("Preview updated top-level before writing to file? (y/N): ").upper()
            == "Y"
        )

    def confirm_update(self, filepath: str) -> bool:
        """Prompt the user to confirm updating an existing file.

        Args:
            filepath: Path to the file that would be updated.

        Returns:
            True if the user does NOT answer 'n' or 'N', False if they do.
        """
        return (
            input(f"Are you sure you want to update {filepath}? (Y/n): ").upper()
            != "N"
        )


class AutomatedInteractionHandler(InteractionHandler):
    """InteractionHandler for automated/headless usage without user prompts.

    All decisions are resolved using pre-configured defaults, making this
    handler suitable for scripted pipelines, CI environments, and unit tests.
    """

    def __init__(
        self,
        overwrite: bool = False,
        preview: bool = False,
        update: bool = True,
    ) -> None:
        """Initialise with fixed policy values.

        Args:
            overwrite: Policy for confirm_overwrite (default: False — do not
                overwrite unless force_overwrite is set on the caller).
            preview: Policy for confirm_preview (default: False — skip preview).
            update: Policy for confirm_update (default: True — proceed with
                update).
        """
        self._overwrite = overwrite
        self._preview = preview
        self._update = update

    def confirm_overwrite(self, filepath: str) -> bool:
        """Return the configured overwrite policy without prompting.

        Args:
            filepath: Ignored; present for interface compatibility.

        Returns:
            The overwrite value set at construction time.
        """
        return self._overwrite

    def confirm_preview(self) -> bool:
        """Return the configured preview policy without prompting.

        Returns:
            The preview value set at construction time.
        """
        return self._preview

    def confirm_update(self, filepath: str) -> bool:
        """Return the configured update policy without prompting.

        Args:
            filepath: Ignored; present for interface compatibility.

        Returns:
            The update value set at construction time.
        """
        return self._update
