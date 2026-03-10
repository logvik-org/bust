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

    def test_default_overwrite_is_false(self):
        handler = AutomatedInteractionHandler()
        self.assertFalse(handler.confirm_overwrite("/some/file.txt"))

    def test_default_preview_is_false(self):
        handler = AutomatedInteractionHandler()
        self.assertFalse(handler.confirm_preview())

    def test_default_update_is_true(self):
        handler = AutomatedInteractionHandler()
        self.assertTrue(handler.confirm_update("/some/file.txt"))

    def test_custom_overwrite_true(self):
        handler = AutomatedInteractionHandler(overwrite=True)
        self.assertTrue(handler.confirm_overwrite("/some/file.txt"))

    def test_custom_preview_true(self):
        handler = AutomatedInteractionHandler(preview=True)
        self.assertTrue(handler.confirm_preview())

    def test_custom_update_false(self):
        handler = AutomatedInteractionHandler(update=False)
        self.assertFalse(handler.confirm_update("/some/file.txt"))


class TestWriteStringToFile(unittest.TestCase):
    """Tests for write_string_to_file using AutomatedInteractionHandler."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    # ------------------------------------------------------------------
    # Basic write behaviour
    # ------------------------------------------------------------------

    def test_writes_new_file(self):
        result = write_string_to_file("hello", "out.txt", self.tmpdir)
        self.assertTrue(result)
        with open(os.path.join(self.tmpdir, "out.txt")) as f:
            self.assertEqual(f.read(), "hello")

    def test_raises_when_dir_does_not_exist(self):
        with self.assertRaises(RuntimeError):
            write_string_to_file("hello", "out.txt", "/nonexistent/dir/xyz")

    # ------------------------------------------------------------------
    # force_overwrite=True bypasses handler entirely
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # interaction_handler controls overwrite decision
    # ------------------------------------------------------------------

    def test_automated_handler_denies_overwrite_by_default(self):
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        handler = AutomatedInteractionHandler(overwrite=False)
        result = write_string_to_file(
            "updated", "out.txt", self.tmpdir, interaction_handler=handler
        )
        self.assertFalse(result)
        with open(path) as f:
            self.assertEqual(f.read(), "original")

    def test_automated_handler_allows_overwrite_when_configured(self):
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        handler = AutomatedInteractionHandler(overwrite=True)
        result = write_string_to_file(
            "updated", "out.txt", self.tmpdir, interaction_handler=handler
        )
        self.assertTrue(result)
        with open(path) as f:
            self.assertEqual(f.read(), "updated")

    def test_force_overwrite_takes_precedence_over_handler(self):
        """force_overwrite=True should not even consult the handler."""
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        # Handler would decline, but force_overwrite overrides it
        handler = AutomatedInteractionHandler(overwrite=False)
        result = write_string_to_file(
            "updated",
            "out.txt",
            self.tmpdir,
            force_overwrite=True,
            interaction_handler=handler,
        )
        self.assertTrue(result)
        with open(path) as f:
            self.assertEqual(f.read(), "updated")

    def test_handler_not_called_when_file_does_not_exist(self):
        """Handler should not be consulted when the target file is new."""

        class _TrackingHandler(AutomatedInteractionHandler):
            called = False

            def confirm_overwrite(self, filepath):
                _TrackingHandler.called = True
                return super().confirm_overwrite(filepath)

        handler = _TrackingHandler(overwrite=False)
        write_string_to_file(
            "hello", "brand_new.txt", self.tmpdir, interaction_handler=handler
        )
        self.assertFalse(_TrackingHandler.called)


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
        """If the existing file does not exist, the new top-level is returned unchanged."""
        handler = AutomatedInteractionHandler()
        result = update_module_top_level(
            "/nonexistent/path/module.vhd",
            self._VHDL_TEMPLATE,
            interaction_handler=handler,
        )
        self.assertEqual(result, self._VHDL_TEMPLATE)

    def test_merges_user_sections_and_proceeds(self):
        """With update=True, user sections from the existing file are preserved."""
        existing = self._write("module.vhd", self._VHDL_WITH_USER_CONTENT)
        handler = AutomatedInteractionHandler(update=True)
        result = update_module_top_level(
            existing, self._VHDL_TEMPLATE, interaction_handler=handler
        )
        self.assertIn("library ieee_extras;", result)
        self.assertIn("my_signal <= '1';", result)

    def test_raises_when_user_cancels_update(self):
        """With update=False, an exception is raised to abort the operation."""
        existing = self._write("module.vhd", self._VHDL_WITH_USER_CONTENT)
        handler = AutomatedInteractionHandler(update=False)
        with self.assertRaises(Exception) as ctx:
            update_module_top_level(
                existing, self._VHDL_TEMPLATE, interaction_handler=handler
            )
        self.assertIn("Cancelled", str(ctx.exception))

    def test_preview_does_not_affect_return_value(self):
        """Enabling preview should not change the returned content."""
        existing = self._write("module.vhd", self._VHDL_WITH_USER_CONTENT)
        handler_no_preview = AutomatedInteractionHandler(preview=False, update=True)
        handler_preview = AutomatedInteractionHandler(preview=True, update=True)
        result_no_preview = update_module_top_level(
            existing, self._VHDL_TEMPLATE, interaction_handler=handler_no_preview
        )
        result_preview = update_module_top_level(
            existing, self._VHDL_TEMPLATE, interaction_handler=handler_preview
        )
        self.assertEqual(result_no_preview, result_preview)


if __name__ == "__main__":
    unittest.main()
