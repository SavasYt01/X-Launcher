"""Build and open web-search requests using the user's default browser."""

from dataclasses import dataclass
from urllib.parse import urlencode, urlsplit

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
    if not Gio.AppInfo.launch_default_for_uri(safe_uri, None):
        raise RuntimeError("The default browser could not be opened.")


def open_web_search(query: str) -> None:
    """Open a safely encoded search query in the configured default browser."""
    open_web_uri(build_search_uri(query))
