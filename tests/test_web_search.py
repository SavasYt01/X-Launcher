import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

from web_search import (
    WebSearchResult,
    build_search_uri,
    open_web_uri,
    validate_web_uri,
)


class WebSearchTests(unittest.TestCase):
    def test_builds_google_search_uri_with_encoded_query(self) -> None:
        query = "python GTK & Wayland"
        uri = build_search_uri(query)
        parsed = urlsplit(uri)

        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "www.google.com")
        self.assertEqual(parsed.path, "/search")
        self.assertEqual(parse_qs(parsed.query), {"q": [query]})

    def test_rejects_empty_query(self) -> None:
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            build_search_uri("  ")

    def test_result_keeps_search_terms(self) -> None:
        result = WebSearchResult("GTK on Wayland")
        self.assertEqual(result.query, "GTK on Wayland")

    def test_accepts_http_and_https_urls_for_aliases(self) -> None:
        self.assertEqual(validate_web_uri("https://youtube.com"), "https://youtube.com")
        self.assertEqual(validate_web_uri("http://example.com"), "http://example.com")

    def test_rejects_non_web_and_credentialed_urls(self) -> None:
        for uri in (
            "javascript:alert(1)",
            "file:///etc/passwd",
            "https://user@example.com",
            "https://example.com:invalid",
            "https://example.com/path with spaces",
        ):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                validate_web_uri(uri)

    @patch("web_search.Gio.AppInfo.launch_default_for_uri", return_value=True)
    def test_opens_a_web_uri_with_gio(self, launch_uri: MagicMock) -> None:
        open_web_uri("https://youtube.com")
        launch_uri.assert_called_once_with("https://youtube.com", None)


if __name__ == "__main__":
    unittest.main()
