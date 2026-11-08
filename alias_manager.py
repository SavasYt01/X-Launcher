"""Load and resolve user-defined launcher aliases."""

import json
import logging
import os
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


def load_aliases(path: Path | None = None) -> dict[str, Alias]:
    """Load valid app and HTTP(S) aliases; invalid files fall back to no aliases."""
    aliases_path = path or _default_aliases_path()
    try:
        content = aliases_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError:
        LOGGER.exception("Could not read aliases file %s", aliases_path)
        return {}

    try:
        data: Any = json.loads(content)
    except json.JSONDecodeError:
        LOGGER.warning("Ignoring invalid aliases file: %s", aliases_path)
        return {}

    if not isinstance(data, dict):
        LOGGER.warning("Ignoring malformed aliases file: %s", aliases_path)
        return {}

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
