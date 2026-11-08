"""Build and open web-search requests using the user's default browser."""

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio

from app_launch_context import create_app_launch_context


@dataclass(frozen=True)
class WebSearchResult:
    query: str
    engine: str = "google"


SEARCH_ENGINES: dict[str, tuple[str, str]] = {
    "google": ("g", "https://www.google.com/search"),
    "duckduckgo": ("ddg", "https://duckduckgo.com/"),
    "brave": ("br", "https://search.brave.com/search"),
    "youtube": ("yt", "https://www.youtube.com/results"),
    "github": ("gh", "https://github.com/search"),
}
ENGINE_ALIASES = {
    "g": "google",
    "dd": "duckduckgo",
    "ddg": "duckduckgo",
    "br": "brave",
    "yt": "youtube",
    "gh": "github",
}


def build_search_uri(query: str, engine: str = "google") -> str:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("Web search query cannot be empty.")
    selected_engine = engine.casefold()
    if selected_engine not in SEARCH_ENGINES:
        raise ValueError("Unsupported web search engine.")
    base_uri = SEARCH_ENGINES[selected_engine][1]
    return f"{base_uri}?{urlencode({'search_query' if selected_engine == 'youtube' else 'q': normalized_query})}"


def engine_for_prefix(prefix: str, default_engine: str = "google") -> str:
    if prefix.casefold() == "s":
        if default_engine not in SEARCH_ENGINES:
            return "google"
        return default_engine
    return ENGINE_ALIASES.get(prefix.casefold(), "google")


def validate_web_uri(uri: str) -> str:
    """Return a safe HTTP(S) URL or reject non-web and credentialed URLs."""
    if any(ord(character) <= 0x20 for character in uri):
        raise ValueError("Only HTTP and HTTPS web addresses are supported.")
    try:
        parsed = urlsplit(uri)
        _ = parsed.port
    except ValueError as error:
        raise ValueError("Only HTTP and HTTPS web addresses are supported.") from error
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ValueError("Only HTTP and HTTPS web addresses are supported.")
    return uri


def open_web_uri(uri: str) -> None:
    """Open a validated HTTP(S) URL in the configured default browser."""
    safe_uri = validate_web_uri(uri)
    if not Gio.AppInfo.launch_default_for_uri(safe_uri, create_app_launch_context()):
        raise RuntimeError("The default browser could not be opened.")


def open_web_search(query: str) -> None:
    """Open a safely encoded search query in the configured default browser."""
    open_web_uri(build_search_uri(query))


def open_engine_search(query: str, engine: str = "google") -> None:
    """Open a query using a known search engine."""
    open_web_uri(build_search_uri(query, engine))
