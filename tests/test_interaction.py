"""Unit tests for InteractionHandler and the refactored file utilities."""

import os
import tempfile
import unittest

from bust.interaction import (
    AutomatedInteractionHandler,
    ConsoleInteractionHandler,
    InteractionHandler,
)
from bust.utils.file_utils import update_module_top_level, write_string_to_file


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


class TestWriteStringToFile(unittest.TestCase):
    """Tests for write_string_to_file using AutomatedInteractionHandler."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_writes_new_file(self):
        result = write_string_to_file("hello", "out.txt", self.tmpdir)
        self.assertTrue(result)
        with open(os.path.join(self.tmpdir, "out.txt")) as f:
            self.assertEqual(f.read(), "hello")

    def test_raises_when_dir_does_not_exist(self):
        with self.assertRaises(RuntimeError):
            write_string_to_file("hello", "out.txt", "/nonexistent/dir/xyz")

    def test_force_overwrite_writes_existing_file(self):
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        result = write_string_to_file(
            "updated", "out.txt", self.tmpdir, force_overwrite=True
        )
        self.assertTrue(result)
        with open(path) as f:
            self.assertEqual(f.read(), "updated")

    def test_handler_denies_overwrite(self):
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        result = write_string_to_file(
            "updated",
            "out.txt",
            self.tmpdir,
            interaction_handler=AutomatedInteractionHandler("n"),
        )
        self.assertFalse(result)
        with open(path) as f:
            self.assertEqual(f.read(), "original")

    def test_handler_allows_overwrite(self):
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        result = write_string_to_file(
            "updated",
            "out.txt",
            self.tmpdir,
            interaction_handler=AutomatedInteractionHandler("y"),
        )
        self.assertTrue(result)
        with open(path) as f:
            self.assertEqual(f.read(), "updated")

    def test_force_overwrite_bypasses_handler(self):
        """force_overwrite=True should not consult the handler at all."""
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        result = write_string_to_file(
            "updated",
            "out.txt",
            self.tmpdir,
            force_overwrite=True,
            interaction_handler=AutomatedInteractionHandler("n"),
        )
        self.assertTrue(result)
        with open(path) as f:
            self.assertEqual(f.read(), "updated")

    def test_handler_not_called_when_file_does_not_exist(self):
        """Handler should not be consulted when the target file is new."""
        called = []

        class _TrackingHandler(AutomatedInteractionHandler):
            def __call__(self, prompt):
                called.append(prompt)
                return super().__call__(prompt)

        write_string_to_file(
            "hello",
            "brand_new.txt",
            self.tmpdir,
            interaction_handler=_TrackingHandler("n"),
        )
        self.assertEqual(called, [])


class TestUpdateModuleTopLevel(unittest.TestCase):
    """Tests for update_module_top_level using AutomatedInteractionHandler."""

    _VHDL_TEMPLATE = """\
-- User Libraries Start
-- User Libraries End
-- User Generics Start
-- User Generics End
-- User Ports Start
-- User Ports End
-- User Architecture Start
-- User Architecture End
-- User Logic Start
-- User Logic End
"""

    _VHDL_WITH_USER_CONTENT = """\
-- User Libraries Start
library ieee_extras;
-- User Libraries End
-- User Generics Start
-- User Generics End
-- User Ports Start
-- User Ports End
-- User Architecture Start
-- User Architecture End
-- User Logic Start
  my_signal <= '1';
-- User Logic End
"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def _write(self, filename, content):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w") as f:
            f.write(content)
        return path

    def test_returns_new_top_level_when_file_missing(self):
        result = update_module_top_level(
            "/nonexistent/path/module.vhd",
            self._VHDL_TEMPLATE,
            interaction_handler=AutomatedInteractionHandler("y"),
        )
        self.assertEqual(result, self._VHDL_TEMPLATE)

    def test_merges_user_sections_and_proceeds(self):
        existing = self._write("module.vhd", self._VHDL_WITH_USER_CONTENT)
        result = update_module_top_level(
            existing,
            self._VHDL_TEMPLATE,
            interaction_handler=AutomatedInteractionHandler("y"),
        )
        self.assertIn("library ieee_extras;", result)
        self.assertIn("my_signal <= '1';", result)

    def test_raises_when_user_cancels_update(self):
        existing = self._write("module.vhd", self._VHDL_WITH_USER_CONTENT)
        with self.assertRaises(Exception) as ctx:
            update_module_top_level(
                existing,
                self._VHDL_TEMPLATE,
                interaction_handler=AutomatedInteractionHandler("n"),
            )
        self.assertIn("Cancelled", str(ctx.exception))

    def test_preview_does_not_affect_return_value(self):
        existing = self._write("module.vhd", self._VHDL_WITH_USER_CONTENT)
        # "y" → preview printed AND proceed; "" → no preview AND proceed
        result_with_preview = update_module_top_level(
            existing,
            self._VHDL_TEMPLATE,
            interaction_handler=AutomatedInteractionHandler("y"),
        )
        result_without_preview = update_module_top_level(
            existing,
            self._VHDL_TEMPLATE,
            interaction_handler=AutomatedInteractionHandler(""),
        )
        self.assertEqual(result_with_preview, result_without_preview)


if __name__ == "__main__":
    unittest.main()
