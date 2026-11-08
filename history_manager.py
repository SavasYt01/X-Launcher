"""Persist recently launched desktop application IDs for ranking."""

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MAX_HISTORY = 20
LOGGER = logging.getLogger(__name__)


def _default_history_path() -> Path:
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )
    return data_home / "xlauncher" / "history.json"


def _read_entries(path: Path) -> list[dict[str, str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError:
        LOGGER.exception("Could not read application history from %s", path)
        return []

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError:
        LOGGER.warning("Ignoring invalid application history file: %s", path)
        return []

    if not isinstance(data, list):
        LOGGER.warning("Ignoring malformed application history file: %s", path)
        return []

    entries: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, dict):
            continue
        desktop_id = item.get("desktop_id")
        timestamp = item.get("timestamp")
        if (
            isinstance(desktop_id, str)
            and desktop_id
            and isinstance(timestamp, str)
            and desktop_id not in seen
        ):
            entries.append({"desktop_id": desktop_id, "timestamp": timestamp})
            seen.add(desktop_id)
        if len(entries) == MAX_HISTORY:
            break
    return entries


def load_history_ids(path: Path | None = None) -> list[str]:
    """Return unique desktop IDs from most to least recently launched."""
    history_path = path or _default_history_path()
    return [entry["desktop_id"] for entry in _read_entries(history_path)]


def record_application(desktop_id: str, path: Path | None = None) -> bool:
    """Record a successful launch; return False if persistence fails."""
    if not desktop_id:
        return False

    history_path = path or _default_history_path()
    entries = _read_entries(history_path)
    entries = [entry for entry in entries if entry["desktop_id"] != desktop_id]
    entries.insert(
        0,
        {
            "desktop_id": desktop_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    entries = entries[:MAX_HISTORY]

    temporary_path: Path | None = None
    try:
        history_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=history_path.parent,
            prefix=f".{history_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump(entries, temporary_file, ensure_ascii=False, indent=2)
            temporary_file.write("\n")
            temporary_file.flush()
            os.fsync(temporary_file.fileno())
        os.replace(temporary_path, history_path)
    except OSError:
        LOGGER.exception("Could not save application history to %s", history_path)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception(
                    "Could not remove temporary history file %s", temporary_path
                )
        return False
    return True
