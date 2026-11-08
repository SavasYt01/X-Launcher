"""Load and resolve user-defined launcher aliases."""

import json
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from web_search import validate_web_uri


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Alias:
    key: str
    kind: Literal["app", "web"]
    value: str


def _default_aliases_path() -> Path:
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )
    return data_home / "xlauncher" / "aliases.json"


def _is_web_uri(value: str) -> bool:
    try:
        validate_web_uri(value)
    except ValueError:
        return False
    return True


def load_aliases(
    path: Path | None = None,
    fallback: dict[str, Alias] | None = None,
) -> dict[str, Alias]:
    """Load valid app and HTTP(S) aliases; invalid files fall back to no aliases."""
    aliases_path = path or _default_aliases_path()
    try:
        content = aliases_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except (OSError, UnicodeError):
        LOGGER.exception("Could not read aliases file %s", aliases_path)
        return fallback.copy() if fallback is not None else {}

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError:
        LOGGER.warning("Ignoring invalid aliases file: %s", aliases_path)
        return fallback.copy() if fallback is not None else {}

    if not isinstance(data, dict):
        LOGGER.warning("Ignoring malformed aliases file: %s", aliases_path)
        return fallback.copy() if fallback is not None else {}

    aliases: dict[str, Alias] = {}
    for key, definition in data.items():
        if (
            not isinstance(key, str)
            or not key
            or any(character.isspace() for character in key)
        ):
            continue
        if not isinstance(definition, dict):
            continue
        kind = definition.get("type")
        value = definition.get("value")
        if not isinstance(value, str) or not value:
            continue
        if kind == "app":
            aliases[key.casefold()] = Alias(key=key, kind="app", value=value)
        elif kind == "web" and _is_web_uri(value):
            aliases[key.casefold()] = Alias(key=key, kind="web", value=value)
    return aliases


def resolve_alias(query: str, aliases: dict[str, Alias]) -> Alias | None:
    """Resolve a complete query as a case-insensitive alias key."""
    return aliases.get(query.strip().casefold())


def save_aliases(
    aliases: dict[str, Alias],
    path: Path | None = None,
) -> bool:
    aliases_path = path or _default_aliases_path()
    payload = {
        alias.key: {"type": alias.kind, "value": alias.value}
        for alias in aliases.values()
    }
    temporary_path: Path | None = None
    try:
        aliases_path.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(aliases_path.parent, 0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{aliases_path.name}.",
            suffix=".tmp",
            dir=aliases_path.parent,
        )
        temporary_path = Path(temporary_name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            os.fchmod(file.fileno(), 0o600)
            json.dump(payload, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, aliases_path)
        os.chmod(aliases_path, 0o600)
    except OSError:
        LOGGER.exception("Takma adlar kaydedilemedi: %s", aliases_path)
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                LOGGER.exception("Geçici takma ad dosyası silinemedi: %s", temporary_path)
        return False
    return True
