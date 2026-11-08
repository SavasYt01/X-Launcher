import json
import tempfile
import unittest
from pathlib import Path

from theme_manager import DEFAULT_THEME_CSS, load_theme


class ThemeManagerTests(unittest.TestCase):
    def test_uses_bundled_default_when_user_theme_is_not_installed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = load_theme(Path(temporary))

        self.assertEqual(result.css, DEFAULT_THEME_CSS)
        self.assertIsNone(result.warning)

    def test_missing_custom_theme_falls_back_to_default_css(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_home = Path(temporary)
            app_dir = data_home / "xlauncher"
            app_dir.mkdir()
            (app_dir / "config.json").write_text(
                json.dumps({"active_theme": "not-installed"}),
                encoding="utf-8",
            )

            result = load_theme(data_home)

        self.assertEqual(result.css, DEFAULT_THEME_CSS)
        self.assertEqual(
            result.warning, "Tema yüklenemedi, varsayılan kullanılıyor."
        )

    def test_loads_configured_theme_css(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_home = Path(temporary)
            app_dir = data_home / "xlauncher"
            theme_dir = app_dir / "themes" / "nord"
            theme_dir.mkdir(parents=True)
            (app_dir / "config.json").write_text(
                json.dumps({"active_theme": "nord"}),
                encoding="utf-8",
            )
            custom_css = ".launcher-surface { background-color: #2e3440; }"
            (theme_dir / "theme.css").write_text(custom_css, encoding="utf-8")

            result = load_theme(data_home)

        self.assertEqual(result.css, custom_css)
        self.assertIsNone(result.warning)

    def test_rejects_theme_names_that_escape_the_theme_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_home = Path(temporary)
            app_dir = data_home / "xlauncher"
            app_dir.mkdir()
            (app_dir / "config.json").write_text(
                json.dumps({"active_theme": "../../outside"}),
                encoding="utf-8",
            )

            result = load_theme(data_home)

        self.assertEqual(result.css, DEFAULT_THEME_CSS)
        self.assertEqual(
            result.warning, "Tema adı geçersiz, varsayılan kullanılıyor."
        )

    def test_invalid_config_falls_back_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_home = Path(temporary)
            app_dir = data_home / "xlauncher"
            app_dir.mkdir()
            (app_dir / "config.json").write_text("{broken", encoding="utf-8")

            result = load_theme(data_home)

        self.assertEqual(result.css, DEFAULT_THEME_CSS)
        self.assertEqual(
            result.warning, "Tema ayarları geçersiz, varsayılan kullanılıyor."
        )

    def test_invalid_css_uses_default_theme(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            data_home = Path(temporary)
            theme_dir = data_home / "xlauncher" / "themes" / "broken"
            theme_dir.mkdir(parents=True)
            (data_home / "xlauncher" / "config.json").write_text(
                json.dumps({"active_theme": "broken"}),
                encoding="utf-8",
            )
            (theme_dir / "theme.css").write_text(
                "entry { this-is-not-a-css-property: #fff; }",
                encoding="utf-8",
            )

            result = load_theme(data_home)

        self.assertEqual(result.css, DEFAULT_THEME_CSS)
        self.assertEqual(
            result.warning, "Tema dosyası geçersiz, varsayılan kullanılıyor."
        )

    def test_shipped_default_theme_is_valid_gtk_css(self) -> None:
        theme_file = (
            Path(__file__).resolve().parents[1]
            / "themes"
            / "default-dark"
            / "theme.css"
        )
        self.assertEqual(
            theme_file.read_text(encoding="utf-8"),
            DEFAULT_THEME_CSS,
        )


if __name__ == "__main__":
    unittest.main()
