import tempfile
import unittest
from pathlib import Path

from file_search import index_home_files, resolve_home_path, search_files


class FileSearchTests(unittest.TestCase):
    def test_searches_files_and_directories_under_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            photo = root / "fotoğraf.png"
            photo.write_text("image", encoding="utf-8")
            downloads = root / "İndirilenler"
            downloads.mkdir()

            indexed = index_home_files(root=root)
            results = search_files("fotoğraf", indexed)
            directory_results = search_files("indirilenler", indexed)

        self.assertEqual([result.path.name for result in results], ["fotoğraf.png"])
        self.assertEqual([result.path.name for result in directory_results], ["İndirilenler"])

    def test_does_not_follow_symlinks_outside_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "home"
            outside = Path(temporary) / "outside"
            root.mkdir()
            outside.mkdir()
            secret = outside / "secret.txt"
            secret.write_text("secret", encoding="utf-8")
            (root / "shortcut").symlink_to(outside, target_is_directory=True)

            indexed = index_home_files(root=root)

        self.assertNotIn(secret, indexed)

    def test_revalidates_file_path_when_opened(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "home"
            outside = Path(temporary) / "outside.txt"
            root.mkdir()
            outside.write_text("outside", encoding="utf-8")
            shortcut = root / "shortcut"
            shortcut.symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "Sembolik bağlantılar"):
                resolve_home_path(shortcut, root=root)
            with self.assertRaisesRegex(ValueError, "kullanıcı dizini"):
                resolve_home_path(outside, root=root)

    def test_limits_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for index in range(20):
                (root / f"photo-{index}.png").touch()
            indexed = index_home_files(root=root)

        self.assertEqual(len(search_files("photo", indexed, limit=2)), 2)
        self.assertEqual(len(search_files("photo", indexed, limit=100)), 15)


if __name__ == "__main__":
    unittest.main()
