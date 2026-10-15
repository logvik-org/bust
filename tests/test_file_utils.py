"""Unit tests for bust.utils.file_utils."""

import os
import tempfile
import unittest
from unittest import mock

from bust.interaction import AutomatedInteractionHandler
from bust.utils.file_utils import write_string_to_file


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

    def test_existing_file_without_terminal_raises(self):
        path = os.path.join(self.tmpdir, "out.txt")
        with open(path, "w") as f:
            f.write("original")
        with mock.patch("sys.stdin.isatty", return_value=False):
            with self.assertRaises(FileExistsError):
                write_string_to_file("updated", "out.txt", self.tmpdir)
        with open(path) as f:
            self.assertEqual(f.read(), "original")

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


if __name__ == "__main__":
    unittest.main()
