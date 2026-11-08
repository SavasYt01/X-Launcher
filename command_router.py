"""Route launcher queries to built-in commands without executing shell input."""

import re
from dataclasses import dataclass
from typing import Any

from alias_manager import Alias
from providers import convert_units, date_time_result
from web_search import ENGINE_ALIASES, engine_for_prefix


_ARITHMETIC_QUERY = re.compile(r"[0-9.\s+\-*/%()]+\Z")


@dataclass(frozen=True)
class QueryRoute:
    kind: str
    value: Any = None


def route_query(
    query: str,
    alias: Alias | None = None,
    default_engine: str = "google",
) -> QueryRoute:
    trimmed = query.strip()
    if alias is not None:
        return QueryRoute("alias", alias)
    if not trimmed:
        return QueryRoute("empty")

    lowered = trimmed.casefold()
    if lowered == "help":
        return QueryRoute("help")
    if lowered.startswith("="):
        return QueryRoute("calculator", trimmed[1:].strip())
    if lowered in {"cb", "cb clear"}:
        return QueryRoute("clipboard", "clear" if lowered == "cb clear" else "list")
    parts = trimmed.split(maxsplit=1)
    if len(parts) == 2 and parts[0].casefold() in {"f", "file"}:
        return QueryRoute("file_search", parts[1].strip())
    if (
        _ARITHMETIC_QUERY.fullmatch(trimmed)
        and any(operator in trimmed for operator in "+-*/%")
    ):
        return QueryRoute("calculator", trimmed)
    if lowered in {"time", "today", "date"}:
        return QueryRoute("provider", date_time_result(lowered))

    prefix, separator, search_query = trimmed.partition(" ")
    if separator and prefix.casefold() in {*ENGINE_ALIASES, "s"}:
        engine = engine_for_prefix(prefix, default_engine)
        if search_query.strip():
            return QueryRoute("web_search", (search_query.strip(), engine))
        return QueryRoute("error", "Aramak için bir ifade yaz.")

    conversion = convert_units(trimmed)
    if conversion is not None:
        return QueryRoute("provider", conversion)
    return QueryRoute("applications", trimmed)
