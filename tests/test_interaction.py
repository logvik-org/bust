"""Unit tests for bust.interaction (InteractionHandler interface)."""

import unittest

from bust.interaction import (
    AutomatedInteractionHandler,
    ConsoleInteractionHandler,
    InteractionHandler,
)


class TestInteractionHandlerInterface(unittest.TestCase):
    """Verify that InteractionHandler is an abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """InteractionHandler must not be directly instantiable."""
        with self.assertRaises(TypeError):
            InteractionHandler()  # type: ignore[abstract]

    def test_console_handler_is_subclass(self):
        self.assertTrue(issubclass(ConsoleInteractionHandler, InteractionHandler))

    def test_automated_handler_is_subclass(self):
        self.assertTrue(issubclass(AutomatedInteractionHandler, InteractionHandler))


class TestAutomatedInteractionHandler(unittest.TestCase):
    """Tests for AutomatedInteractionHandler behaviour."""

    def test_returns_configured_default(self):
        handler = AutomatedInteractionHandler("y")
        self.assertEqual(handler("Any prompt?"), "y")

    def test_empty_string_default(self):
        handler = AutomatedInteractionHandler()
        self.assertEqual(handler("Any prompt?"), "")

    def test_response_is_independent_of_prompt(self):
        handler = AutomatedInteractionHandler("yes")
        self.assertEqual(handler("Prompt A"), "yes")
        self.assertEqual(handler("Prompt B"), "yes")


if __name__ == "__main__":
    unittest.main()
