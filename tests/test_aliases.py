import json
import tempfile
import unittest
from pathlib import Path

from alias_manager import Alias, load_aliases, resolve_alias


class AliasManagerTests(unittest.TestCase):
    def test_loads_and_matches_app_and_web_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "aliases.json"
            path.write_text(
                json.dumps(
                    {
                        "vs": {"type": "app", "value": "code.desktop"},
                        "yt": {"type": "web", "value": "https://youtube.com"},
                    }
                ),
                encoding="utf-8",
            )

            aliases = load_aliases(path)

        self.assertEqual(
            resolve_alias(" VS ", aliases),
            Alias(key="vs", kind="app", value="code.desktop"),
        )
        self.assertEqual(
            resolve_alias("YT", aliases),
            Alias(key="yt", kind="web", value="https://youtube.com"),
        )
        self.assertIsNone(resolve_alias("youtube", aliases))

    def test_ignores_invalid_json_and_unsafe_web_urls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "aliases.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(load_aliases(path), {})

            path.write_text(
                json.dumps(
                    {
                        "safe": {"type": "web", "value": "https://example.com"},
                        "unsafe": {"type": "web", "value": "javascript:alert(1)"},
                        "invalid": {"type": "other", "value": "anything"},
                    }
                ),
                encoding="utf-8",
            )
            aliases = load_aliases(path)

        self.assertEqual(set(aliases), {"safe"})


if __name__ == "__main__":
    unittest.main()
