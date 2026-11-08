import unittest
from types import SimpleNamespace

from fuzzy_search import search_applications


class FuzzySearchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.applications = [
            SimpleNamespace(
                name="Firefox", comment="Web Browser", desktop_id="firefox.desktop"
            ),
            SimpleNamespace(
                name="Google Chrome", comment="Web Browser", desktop_id="chrome.desktop"
            ),
            SimpleNamespace(
                name="Files", comment="File Manager", desktop_id="files.desktop"
            ),
        ]

    def test_matches_non_contiguous_initials(self) -> None:
        results = search_applications(self.applications, "ff")
        self.assertEqual(results[0].name, "Firefox")

    def test_matches_a_contiguous_name_fragment(self) -> None:
        results = search_applications(self.applications, "chr")
        self.assertEqual(results[0].name, "Google Chrome")

    def test_empty_query_returns_no_results(self) -> None:
        self.assertEqual(search_applications(self.applications, "  "), [])

    def test_recent_application_gets_a_small_ranking_boost(self) -> None:
        applications = [
            SimpleNamespace(
                name="File Manager", comment="", desktop_id="manager.desktop"
            ),
            SimpleNamespace(name="Files", comment="", desktop_id="files.desktop"),
        ]

        results = search_applications(
            applications, "file", history_ids=["manager.desktop"]
        )

        self.assertEqual(results[0].desktop_id, "manager.desktop")

    def test_generic_name_is_weaker_than_a_direct_application_name_match(self) -> None:
        applications = [
            SimpleNamespace(
                name="Firefox",
                generic_name="Browser",
                comment="",
                desktop_id="firefox.desktop",
            ),
            SimpleNamespace(
                name="Browser Utility",
                generic_name="",
                comment="",
                desktop_id="browser.desktop",
            ),
        ]

        results = search_applications(applications, "browser")

        self.assertEqual(results[0].desktop_id, "browser.desktop")


if __name__ == "__main__":
    unittest.main()
