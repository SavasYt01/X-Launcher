"""Store and manage favorite desktop application IDs."""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)


def _default_path() -> Path:
    data_home = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return data_home / "xlauncher" / "favorites.json"


class FavoritesManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or _default_path()

    def load(self, valid_ids: set[str] | None = None) -> list[str]:
        try:
            data: Any = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, json.JSONDecodeError):
            LOGGER.exception("Favoriler okunamadı: %s", self.path)
            return []
        if not isinstance(data, list):
            LOGGER.warning("Favori dosyası geçersiz: %s", self.path)
            return []
        favorites = list(
            dict.fromkeys(item for item in data if isinstance(item, str) and item)
        )
        if valid_ids is not None:
            filtered = [item for item in favorites if item in valid_ids]
            if filtered != favorites:
                self.save(filtered)
            favorites = filtered
        return favorites

    def contains(self, desktop_id: str) -> bool:
        return desktop_id in self.load()

    def toggle(self, desktop_id: str, valid_ids: set[str] | None = None) -> bool:
        if not desktop_id or (valid_ids is not None and desktop_id not in valid_ids):
            return False
        favorites = self.load(valid_ids)
        if desktop_id in favorites:
            favorites.remove(desktop_id)
        else:
            favorites.append(desktop_id)
        return self.save(favorites)

    def save(self, favorites: list[str]) -> bool:
        unique = list(dict.fromkeys(item for item in favorites if item))
        temporary_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(self.path.parent, 0o700)
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
            )
            temporary_path = Path(temporary_name)
            with os.fdopen(descriptor, "w", encoding="utf-8") as file:
                os.fchmod(file.fileno(), 0o600)
                json.dump(unique, file, ensure_ascii=False, indent=2)
                file.write("\n")
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, self.path)
            os.chmod(self.path, 0o600)
        except OSError:
            LOGGER.exception("Favoriler kaydedilemedi: %s", self.path)
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    LOGGER.exception("Geçici favori dosyası silinemedi: %s", temporary_path)
            return False
        return True
