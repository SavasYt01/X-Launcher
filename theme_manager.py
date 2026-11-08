"""Load a user-selected GTK4 CSS theme with a safe built-in fallback."""

import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from config_manager import ConfigManager, default_config_path

DEFAULT_THEME_NAME = "default-dark"
_THEME_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")
LOGGER = logging.getLogger(__name__)

DEFAULT_THEME_CSS = """\
window.launcher-window {
  background-color: transparent;
}

.launcher-surface {
  background-color: #000000;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}

entry.launcher-entry {
  min-height: 32px;
  padding: 12px 18px;
  border: none;
  border-radius: 12px;
  background-color: transparent;
  background-image: none;
  box-shadow: none;
  color: #ffffff;
  caret-color: #ffffff;
  font-family: "SF Pro Display", sans-serif;
  font-size: 16pt;
}

entry.launcher-entry:focus {
  outline: none;
  box-shadow: none;
}

list.launcher-results,
list.launcher-results row {
  background-color: transparent;
  color: #ffffff;
}

list.launcher-results row {
  min-height: 56px;
  padding: 8px 16px;
  border-radius: 8px;
}

list.launcher-results row:selected {
  background-color: #252525;
}

.launcher-description,
.launcher-status {
  color: #aaaaaa;
  font-size: 10pt;
}

.launcher-status {
  padding: 0 18px 8px;
}
"""


@dataclass(frozen=True)
class ThemeLoadResult:
    css: str
    warning: str | None = None


def _is_valid_css(css: str) -> bool:
    provider = Gtk.CssProvider()
    errors: list[str] = []

    def on_parsing_error(
        css_provider: Gtk.CssProvider,
        section: Gtk.CssSection,
        error: Exception,
    ) -> None:
        _ = css_provider, section
        errors.append(str(error))

    provider.connect("parsing-error", on_parsing_error)
    try:
        provider.load_from_string(css)
    except (TypeError, ValueError):
        return False
    return not errors


def _fallback(warning: str) -> ThemeLoadResult:
    LOGGER.warning(warning)
    return ThemeLoadResult(DEFAULT_THEME_CSS, warning)


def load_theme(data_home: Path | None = None) -> ThemeLoadResult:
    """Load configured theme CSS or return the built-in dark stylesheet."""
    if data_home is None:
        config_manager = ConfigManager()
        root = default_config_path().parent.parent
    else:
        config_manager = ConfigManager(data_home / "xlauncher" / "config.json")
        root = data_home
    try:
        raw_config = json.loads(config_manager.path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raw_config = {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _fallback("Tema ayarları geçersiz, varsayılan kullanılıyor.")
    if not isinstance(raw_config, dict):
        return _fallback("Tema ayarları geçersiz, varsayılan kullanılıyor.")
    configured_theme = raw_config.get("active_theme", DEFAULT_THEME_NAME)
    if (
        not isinstance(configured_theme, str)
        or _THEME_NAME_PATTERN.fullmatch(configured_theme) is None
    ):
        return _fallback("Tema adı geçersiz, varsayılan kullanılıyor.")

    theme_name = config_manager.values["active_theme"]
    if config_manager.warning:
        return _fallback("Tema ayarları geçersiz, varsayılan kullanılıyor.")
    theme_path = root / "xlauncher" / "themes" / theme_name / "theme.css"
    try:
        css = theme_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        if theme_name != DEFAULT_THEME_NAME:
            return _fallback("Tema yüklenemedi, varsayılan kullanılıyor.")
        bundled_theme = Path(__file__).resolve().parent / "themes" / theme_name / "theme.css"
        try:
            css = bundled_theme.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return _fallback("Tema yüklenemedi, varsayılan kullanılıyor.")
    except (OSError, UnicodeError):
        return _fallback("Tema yüklenemedi, varsayılan kullanılıyor.")

    if not css.strip():
        return _fallback("Tema dosyası boş, varsayılan kullanılıyor.")
    if not _is_valid_css(css):
        return _fallback("Tema dosyası geçersiz, varsayılan kullanılıyor.")
    return ThemeLoadResult(css)
