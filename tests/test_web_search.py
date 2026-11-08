import unittest
from urllib.parse import parse_qs, urlsplit

from web_search import WebSearchResult, build_search_uri


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


if __name__ == "__main__":
    unittest.main()
