import unittest
from types import SimpleNamespace

from fuzzy_search import search_applications


class FuzzySearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.applications = [
            SimpleNamespace(name="Firefox", comment="Web Browser"),
            SimpleNamespace(name="Google Chrome", comment="Web Browser"),
            SimpleNamespace(name="Files", comment="File Manager"),
        ]

    def test_matches_non_contiguous_initials(self) -> None:
        results = search_applications(self.applications, "ff")
        self.assertEqual(results[0].name, "Firefox")

    def test_matches_a_contiguous_name_fragment(self) -> None:
        results = search_applications(self.applications, "chr")
        self.assertEqual(results[0].name, "Google Chrome")

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(search_applications(self.applications, "  "), [])


if __name__ == "__main__":
    unittest.main()
