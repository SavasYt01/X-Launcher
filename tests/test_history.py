import json
import tempfile
import unittest
from pathlib import Path

from history_manager import MAX_HISTORY, load_history_ids, record_application


class HistoryManagerTests(unittest.TestCase):
    def test_saves_and_loads_most_recent_applications(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "nested" / "history.json"

            self.assertTrue(record_application("firefox.desktop", path))
            self.assertTrue(record_application("code.desktop", path))
            self.assertTrue(record_application("firefox.desktop", path))

            self.assertEqual(
                load_history_ids(path),
                ["firefox.desktop", "code.desktop"],
            )
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("timestamp", data[0])

    def test_keeps_only_the_last_twenty_unique_apps(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "history.json"

            for index in range(MAX_HISTORY + 3):
                self.assertTrue(record_application(f"app-{index}.desktop", path))

            history = load_history_ids(path)
            self.assertEqual(len(history), MAX_HISTORY)
            self.assertEqual(history[0], f"app-{MAX_HISTORY + 2}.desktop")
            self.assertNotIn("app-0.desktop", history)

    def test_recovers_from_corrupt_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "history.json"
            path.write_text("{broken", encoding="utf-8")

            self.assertEqual(load_history_ids(path), [])
            self.assertTrue(record_application("firefox.desktop", path))
            self.assertEqual(load_history_ids(path), ["firefox.desktop"])


if __name__ == "__main__":
    unittest.main()
