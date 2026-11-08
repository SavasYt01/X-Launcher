import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import MagicMock, patch

from web_search import (
    SEARCH_ENGINES,
    WebSearchResult,
    build_search_uri,
    open_engine_search,
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
        with self.assertRaisesRegex(ValueError, "bir ifade yazın"):
            build_search_uri("  ")

    def test_result_keeps_search_terms(self) -> None:
        result = WebSearchResult("GTK on Wayland")
        self.assertEqual(result.query, "GTK on Wayland")

    def test_builds_correct_query_parameters_for_every_engine(self) -> None:
        query = "X-Launcher müzik & GTK"
        for engine, (_, base_uri) in SEARCH_ENGINES.items():
            with self.subTest(engine=engine):
                parsed = urlsplit(build_search_uri(query, engine))
                expected_parameter = "search_query" if engine == "youtube" else "q"
                self.assertEqual(
                    parse_qs(parsed.query),
                    {expected_parameter: [query]},
                )
                self.assertEqual(
                    f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                    base_uri,
                )

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
    @patch("web_search.create_app_launch_context", return_value=object())
    def test_opens_a_web_uri_with_gio(
        self,
        launch_context: MagicMock,
        launch_uri: MagicMock,
    ) -> None:
        open_web_uri("https://youtube.com")
        launch_uri.assert_called_once_with(
            "https://youtube.com",
            launch_context.return_value,
        )

    @patch("web_search.Gio.AppInfo.launch_default_for_uri", return_value=True)
    @patch("web_search.create_app_launch_context", return_value=object())
    def test_opens_engine_search_using_default_browser(
        self,
        launch_context: MagicMock,
        launch_uri: MagicMock,
    ) -> None:
        query = "müzik & GTK"
        open_engine_search(query, "youtube")

        args, _ = launch_uri.call_args
        self.assertEqual(
            parse_qs(urlsplit(args[0]).query),
            {"search_query": [query]},
        )
        self.assertEqual(args[1], launch_context.return_value)

    @patch("web_search.Gio.AppInfo.launch_default_for_uri", return_value=False)
    @patch("web_search.create_app_launch_context", return_value=None)
    def test_reports_default_browser_failure_in_turkish(
        self,
        _launch_context: MagicMock,
        _launch_uri: MagicMock,
    ) -> None:
        _ = _launch_context, _launch_uri
        with self.assertRaisesRegex(RuntimeError, "Varsayılan tarayıcı"):
            open_engine_search("python")


if __name__ == "__main__":
    unittest.main()
