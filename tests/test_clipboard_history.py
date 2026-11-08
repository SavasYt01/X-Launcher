import tempfile
import unittest
from pathlib import Path

from clipboard_history import (
    clear_clipboard_history,
    load_clipboard_history,
    record_clipboard_text,
)


class ClipboardHistoryTests(unittest.TestCase):
    def test_records_only_explicit_text_deduplicates_and_limits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clipboard_history.json"
            self.assertFalse(record_clipboard_text("ignored", path, enabled=False))
            self.assertTrue(record_clipboard_text("one", path, limit=2, enabled=True))
            self.assertTrue(record_clipboard_text("two", path, limit=2, enabled=True))
            self.assertTrue(record_clipboard_text("one", path, limit=2, enabled=True))

            entries = load_clipboard_history(path, limit=2)

        self.assertEqual([entry.text for entry in entries], ["one", "two"])

    def test_corrupt_data_and_clear(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clipboard_history.json"
            path.write_text("{bad", encoding="utf-8")
            self.assertEqual(load_clipboard_history(path), [])
            self.assertTrue(clear_clipboard_history(path))
            self.assertFalse(path.exists())

    def test_invalid_utf8_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "clipboard_history.json"
            path.write_bytes(b"\xff")

            self.assertEqual(load_clipboard_history(path), [])


if __name__ == "__main__":
    unittest.main()
