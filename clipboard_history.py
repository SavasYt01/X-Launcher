"""Persist only text explicitly copied by X-Launcher."""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_manager import ConfigManager


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ClipboardEntry:
    text: str
    timestamp: str


def _default_path() -> Path:
    return ConfigManager().path.parent / "clipboard_history.json"


def load_clipboard_history(
    path: Path | None = None,
    limit: int | None = None,
) -> list[ClipboardEntry]:
    config = ConfigManager()
    history_path = path or config.path.parent / "clipboard_history.json"
    maximum = limit if limit is not None else config.values["max_clipboard_history"]
    try:
        data: Any = json.loads(history_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError, json.JSONDecodeError):
        LOGGER.exception("Pano geçmişi okunamadı: %s", history_path)
        return []
    if not isinstance(data, list):
        LOGGER.warning("Pano geçmişi biçimi geçersiz: %s", history_path)
        return []
    entries: list[ClipboardEntry] = []
    seen: set[str] = set()
    for item in data:
        if (
            isinstance(item, dict)
            and isinstance(item.get("text"), str)
            and item["text"]
            and isinstance(item.get("timestamp"), str)
            and item["text"] not in seen
        ):
            entries.append(ClipboardEntry(item["text"], item["timestamp"]))
            seen.add(item["text"])
            if len(entries) >= max(1, maximum):
                break
    return entries


def record_clipboard_text(
    text: str,
    path: Path | None = None,
    limit: int | None = None,
    enabled: bool | None = None,
) -> bool:
    """Record an explicit launcher-originated copy; never monitors system clipboard."""
    config = ConfigManager()
    is_enabled = (
        enabled
        if enabled is not None
        else config.values["clipboard_history_enabled"]
    )
    if not is_enabled or not text:
        return False
    history_path = path or config.path.parent / "clipboard_history.json"
    maximum = limit if limit is not None else config.values["max_clipboard_history"]
    entries = load_clipboard_history(history_path, maximum)
    timestamp = datetime.now(timezone.utc).isoformat()
    updated = [ClipboardEntry(text, timestamp)]
    updated.extend(entry for entry in entries if entry.text != text)
    payload = [
        {"text": entry.text, "timestamp": entry.timestamp}
        for entry in updated[: max(1, maximum)]
    ]
    temporary_path: Path | None = None
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(history_path.parent, 0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{history_path.name}.",
            suffix=".tmp",
            dir=history_path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            os.fchmod(file.fileno(), 0o600)
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, history_path)
        os.chmod(history_path, 0o600)
    except OSError:
        LOGGER.exception("Pano geçmişi kaydedilemedi: %s", history_path)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("Geçici pano geçmişi silinemedi: %s", temporary_path)
        return False
    return True


def clear_clipboard_history(path: Path | None = None) -> bool:
    history_path = path or _default_path()
    try:
        history_path.unlink(missing_ok=True)
    except OSError:
        LOGGER.exception("Pano geçmişi temizlenemedi: %s", history_path)
        return False
    return True
