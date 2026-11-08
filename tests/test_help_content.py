import unittest

from help_content import HELP_ENTRIES, QUICK_HELP_ENTRIES


class HelpContentTests(unittest.TestCase):
    def test_quick_help_exposes_calculator_file_clipboard_and_help(self) -> None:
        descriptions = " ".join(
            f"{entry.title} {entry.description}"
            for entry in QUICK_HELP_ENTRIES
        ).casefold()

        for expected in ("5*3", "f fotoğraf.png", "cb", "help"):
            with self.subTest(expected=expected):
                self.assertIn(expected.casefold(), descriptions)

    def test_full_help_contains_all_quick_entries(self) -> None:
        self.assertTrue(all(entry in HELP_ENTRIES for entry in QUICK_HELP_ENTRIES))


if __name__ == "__main__":
    unittest.main()
