import json
import tempfile
import unittest
from pathlib import Path

from favorites_manager import FavoritesManager


class FavoritesManagerTests(unittest.TestCase):
    def test_toggle_add_remove_and_validate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manager = FavoritesManager(Path(temporary) / "favorites.json")

            self.assertTrue(manager.toggle("firefox.desktop", {"firefox.desktop"}))
            self.assertEqual(manager.load(), ["firefox.desktop"])
            self.assertFalse(manager.toggle("missing.desktop", {"firefox.desktop"}))
            self.assertTrue(manager.toggle("firefox.desktop", {"firefox.desktop"}))
            self.assertEqual(manager.load(), [])

    def test_corrupt_json_and_stale_ids_are_handled(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "favorites.json"
            manager = FavoritesManager(path)
            path.write_text("{bad", encoding="utf-8")
            self.assertEqual(manager.load(), [])
            path.write_text(
                json.dumps(["installed.desktop", "removed.desktop"]),
                encoding="utf-8",
            )

            self.assertEqual(manager.load({"installed.desktop"}), ["installed.desktop"])


if __name__ == "__main__":
    unittest.main()
