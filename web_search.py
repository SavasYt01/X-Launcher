"""Build and open web-search requests using the user's default browser."""

from dataclasses import dataclass
from urllib.parse import urlencode

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio


@dataclass(frozen=True)
class WebSearchResult:
    query: str


def build_search_uri(query: str) -> str:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Web search query cannot be empty.")
    return f"https://www.google.com/search?{urlencode({'q': normalized_query})}"


def open_web_search(query: str) -> None:
    """Open a safely encoded search query in the configured default browser."""
    uri = build_search_uri(query)
    if not Gio.AppInfo.launch_default_for_uri(uri, None):
        raise RuntimeError("The default browser could not be opened.")
