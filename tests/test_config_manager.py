import json
import os
import tempfile
import unittest
from pathlib import Path

from config_manager import ConfigManager, DEFAULT_CONFIG


class ConfigManagerTests(unittest.TestCase):
    def test_defaults_and_clamps_invalid_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "result_limit": 100,
                        "refresh_interval_seconds": -1,
                        "search_engine": "unknown",
                        "clipboard_history_enabled": "yes",
                    }
                ),
                encoding="utf-8",
            )
            config = ConfigManager(path)

        self.assertEqual(config.values["result_limit"], 20)
        self.assertEqual(config.values["refresh_interval_seconds"], 0)
        self.assertEqual(config.values["search_engine"], "google")
        self.assertTrue(config.values["clipboard_history_enabled"])
        self.assertEqual(config.values["active_theme"], DEFAULT_CONFIG["active_theme"])

    def test_keeps_unknown_fields_and_writes_private_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_text(json.dumps({"future_option": 7}), encoding="utf-8")
            config = ConfigManager(path)

            self.assertTrue(config.save({"result_limit": 12}))
            data = json.loads(path.read_text(encoding="utf-8"))
            permissions = os.stat(path).st_mode & 0o777

        self.assertEqual(data["future_option"], 7)
        self.assertEqual(data["result_limit"], 12)
        self.assertEqual(permissions, 0o600)

    def test_invalid_json_does_not_replace_current_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            config = ConfigManager(path)
            self.assertTrue(config.save({"result_limit": 11}))
            path.write_text("{bad", encoding="utf-8")

            values = config.load()

        self.assertEqual(values["result_limit"], 11)
        self.assertIsNotNone(config.warning)

    def test_invalid_utf8_falls_back_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "config.json"
            path.write_bytes(b"\xff")
            config = ConfigManager(path)

        self.assertEqual(config.values, DEFAULT_CONFIG)
        self.assertIsNotNone(config.warning)


if __name__ == "__main__":
    unittest.main()
