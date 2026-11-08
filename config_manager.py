"""Validated, atomic configuration storage for X-Launcher."""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG: dict[str, Any] = {
    "active_theme": "default-dark",
    "result_limit": 12,
    "search_engine": "google",
    "show_recent_on_empty": True,
    "show_favorites_on_empty": True,
    "max_history": 20,
    "history_boost": 40,
    "refresh_interval_seconds": 60,
    "clipboard_history_enabled": True,
    "max_clipboard_history": 20,
    "show_recent": True,
    "show_favorites": True,
}
_LIMITS = {
    "result_limit": (3, 20),
    "max_history": (1, 200),
    "history_boost": (0, 100),
    "refresh_interval_seconds": (0, 3600),
    "max_clipboard_history": (1, 200),
}
_BOOLEAN_KEYS = {
    "show_recent_on_empty",
    "show_favorites_on_empty",
    "clipboard_history_enabled",
    "show_recent",
    "show_favorites",
}
_ENGINES = {"google", "duckduckgo", "brave"}
_THEME_NAME_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")


def default_config_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "xlauncher" / "config.json"


def _validate_config(data: Any) -> dict[str, Any]:
    values = DEFAULT_CONFIG.copy()
    if not isinstance(data, dict):
        return values
    values.update(data)
    if (
        not isinstance(values["active_theme"], str)
        or _THEME_NAME_PATTERN.fullmatch(values["active_theme"]) is None
    ):
        values["active_theme"] = DEFAULT_CONFIG["active_theme"]
    if (
        not isinstance(values["search_engine"], str)
        or values["search_engine"] not in _ENGINES
    ):
        values["search_engine"] = DEFAULT_CONFIG["search_engine"]
    for key in _BOOLEAN_KEYS:
        if not isinstance(values.get(key), bool):
            values[key] = DEFAULT_CONFIG[key]
    for key, (minimum, maximum) in _LIMITS.items():
        value = values.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            values[key] = DEFAULT_CONFIG[key]
        else:
            values[key] = min(maximum, max(minimum, value))
    return values


class ConfigManager:
    """Keep validated settings and preserve unknown future config keys."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_config_path()
        self.values = DEFAULT_CONFIG.copy()
        self.warning: str | None = None
        self.load()

    def load(self) -> dict[str, Any]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            self.values = DEFAULT_CONFIG.copy()
            self.warning = None
            return self.values.copy()
        except (OSError, UnicodeError):
            LOGGER.exception("Ayar dosyası okunamadı: %s", self.path)
            self.warning = "Ayarlar okunamadı; varsayılan değerler kullanılıyor."
            return self.values.copy()

        try:
            data: Any = json.loads(raw)
        except json.JSONDecodeError:
            LOGGER.warning("Ayar dosyası geçersiz: %s", self.path)
            self.warning = "Ayar dosyası geçersiz; varsayılan değerler kullanılıyor."
            return self.values.copy()
        if not isinstance(data, dict):
            LOGGER.warning("Ayar dosyası nesne değil: %s", self.path)
            self.warning = "Ayar dosyası geçersiz; varsayılan değerler kullanılıyor."
            return self.values.copy()
        self.values = _validate_config(data)
        self.warning = None
        return self.values.copy()

    def save(self, updates: dict[str, Any] | None = None) -> bool:
        candidate = self.values.copy()
        if updates:
            candidate.update(updates)
        validated = _validate_config(candidate)
        temporary_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            current_mode = self.path.parent.stat().st_mode & 0o777
            if current_mode & 0o077:
                os.chmod(self.path.parent, 0o700)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                os.fchmod(file.fileno(), 0o600)
                json.dump(validated, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
            os.chmod(self.path, 0o600)
        except OSError:
            LOGGER.exception("Ayarlar kaydedilemedi: %s", self.path)
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    LOGGER.exception("Geçici ayar dosyası silinemedi: %s", temporary_path)
            return False
        self.values = validated
        self.warning = None
        return True
