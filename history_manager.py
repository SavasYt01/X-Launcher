"""Persist recent application usage for launcher ranking and suggestions."""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config_manager import ConfigManager


MAX_HISTORY = 20
LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HistoryEntry:
    desktop_id: str
    last_used: str
    use_count: int = 1


def _parse_entries(path: Path, max_history: int) -> list[HistoryEntry]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except (OSError, UnicodeError):
        LOGGER.exception("Uygulama geçmişi okunamadı: %s", path)
        return []

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError:
        LOGGER.warning("Bozuk uygulama geçmişi yok sayıldı: %s", path)
        return []

    if isinstance(data, dict):
        data = data.get("applications", [])
    if not isinstance(data, list):
        LOGGER.warning("Uygulama geçmişi biçimi tanınmıyor: %s", path)
        return []

    entries: list[HistoryEntry] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        desktop_id = item.get("desktop_id")
        last_used = item.get("last_used", item.get("timestamp"))
        count = item.get("use_count", 1)
        if (
            not isinstance(desktop_id, str)
            or not desktop_id
            or not isinstance(last_used, str)
            or desktop_id in seen
        ):
            continue
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            count = 1
        entries.append(HistoryEntry(desktop_id, last_used, count))
        seen.add(desktop_id)
        if len(entries) >= max_history:
            break
    return entries


def load_history(
    path: Path | None = None,
    max_history: int | None = None,
) -> list[HistoryEntry]:
    manager = ConfigManager()
    history_path = path or manager.path.parent / "history.json"
    limit = max_history if max_history is not None else manager.values["max_history"]
    return _parse_entries(history_path, max(1, limit))


def load_history_ids(path: Path | None = None) -> list[str]:
    """Return unique desktop IDs from most to least recently launched."""
    return [entry.desktop_id for entry in load_history(path)]


def record_application(
    desktop_id: str,
    path: Path | None = None,
    max_history: int | None = None,
) -> bool:
    """Record a successful launch atomically without blocking the launch."""
    if not desktop_id:
        return False
    manager = ConfigManager()
    history_path = path or manager.path.parent / "history.json"
    limit = max_history if max_history is not None else manager.values["max_history"]
    limit = max(1, limit)
    entries = _parse_entries(history_path, limit)
    previous = next((entry for entry in entries if entry.desktop_id == desktop_id), None)
    updated = HistoryEntry(
        desktop_id,
        datetime.now(timezone.utc).isoformat(),
        previous.use_count + 1 if previous else 1,
    )
    entries = [updated, *(entry for entry in entries if entry.desktop_id != desktop_id)]
    entries = entries[:limit]
    serialized = [
        {
            "desktop_id": entry.desktop_id,
            "last_used": entry.last_used,
            "use_count": entry.use_count,
        }
        for entry in entries
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
            json.dump(serialized, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, history_path)
        os.chmod(history_path, 0o600)
    except OSError:
        LOGGER.exception("Uygulama geçmişi kaydedilemedi: %s", history_path)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("Geçici geçmiş dosyası silinemedi: %s", temporary_path)
        return False
    return True


def clear_history(path: Path | None = None) -> bool:
    manager = ConfigManager()
    history_path = path or manager.path.parent / "history.json"
    try:
        history_path.unlink(missing_ok=True)
    except OSError:
        LOGGER.exception("Uygulama geçmişi temizlenemedi: %s", history_path)
        return False
    return True


def history_scores(
    path: Path | None = None,
    max_history: int | None = None,
    base_boost: int | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    manager = ConfigManager()
    boost = base_boost if base_boost is not None else manager.values["history_boost"]
    current_time = now or datetime.now(timezone.utc)
    scores: dict[str, int] = {}
    for entry in load_history(path, max_history):
        try:
            last_used = datetime.fromisoformat(entry.last_used)
            if last_used.tzinfo is None:
                last_used = last_used.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (current_time - last_used).total_seconds() / 86400)
        except (ValueError, OverflowError):
            age_days = 30.0
        recency = 0.5 ** (age_days / 7.0)
        frequency = min(1.0, 0.5 + 0.1 * (entry.use_count - 1))
        scores[entry.desktop_id] = int(boost * recency * frequency)
    return scores
