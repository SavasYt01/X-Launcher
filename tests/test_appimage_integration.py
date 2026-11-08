import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from appimage_integration import desktop_entry_text, integrate, unintegrate


class AppImageIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="xlauncher appimage ")
        self.root = Path(self.temporary.name)
        self.data_home = self.root / "xdg data"
        self.appdir = self.root / "AppDir"
        self.icon = (
            self.appdir
            / "usr"
            / "share"
            / "icons"
            / "hicolor"
            / "scalable"
            / "apps"
            / "xlauncher.svg"
        )
        self.icon.parent.mkdir(parents=True)
        self.icon.write_text("<svg/>\n", encoding="utf-8")
        self.image = self.root / "X Launcher % test.AppImage"
        self.image.write_bytes(b"AppImage test")
        self.image.chmod(0o755)
        self.environment = patch.dict(
            os.environ,
            {
                "XDG_DATA_HOME": str(self.data_home),
                "APPDIR": str(self.appdir),
                "APPIMAGE": str(self.image),
            },
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.temporary.cleanup)

    def test_desktop_entry_quotes_path_with_spaces_quotes_and_percent(self) -> None:
        image = Path('/tmp/X "Launcher"`$%test.AppImage')
        entry = desktop_entry_text(image)

        self.assertIn(
            'Exec="/tmp/X \\"Launcher\\"\\`\\$%%test.AppImage" --toggle\n',
            entry,
        )
        self.assertIn("X-XLauncher-Managed=true", entry)

    def test_integrate_uses_separate_entry_and_preserves_native_install(self) -> None:
        applications = self.data_home / "applications"
        applications.mkdir(parents=True)
        native_entry = applications / "xlauncher.desktop"
        native_entry.write_text("native install\n", encoding="utf-8")

        self.assertEqual(integrate(appdir=self.appdir), 0)

        desktop_entry = applications / "xlauncher-appimage.desktop"
        icon = (
            self.data_home
            / "icons"
            / "hicolor"
            / "scalable"
            / "apps"
            / "xlauncher-appimage.svg"
        )
        self.assertTrue(desktop_entry.is_file())
        self.assertTrue(icon.is_file())
        self.assertIn(
            f'Exec="{str(self.image).replace("%", "%%")}" --toggle',
            desktop_entry.read_text(),
        )
        self.assertEqual(native_entry.read_text(), "native install\n")

    def test_integrate_refuses_to_replace_unmanaged_entry(self) -> None:
        applications = self.data_home / "applications"
        applications.mkdir(parents=True)
        managed_path = applications / "xlauncher-appimage.desktop"
        managed_path.write_text("unrelated entry\n", encoding="utf-8")

        self.assertEqual(integrate(appdir=self.appdir), 1)
        self.assertEqual(managed_path.read_text(), "unrelated entry\n")

    def test_unintegrate_checks_icon_source_before_removing_entry(self) -> None:
        applications = self.data_home / "applications"
        applications.mkdir(parents=True)
        desktop_path = applications / "xlauncher-appimage.desktop"
        desktop_path.write_text(
            "[Desktop Entry]\nX-XLauncher-Managed=true\n",
            encoding="utf-8",
        )
        self.icon.unlink()

        self.assertEqual(unintegrate(), 1)
        self.assertTrue(desktop_path.is_file())

    def test_unintegrate_refuses_to_run_as_root(self) -> None:
        self.assertEqual(integrate(appdir=self.appdir), 0)
        desktop_path = (
            self.data_home / "applications" / "xlauncher-appimage.desktop"
        )

        with patch("appimage_integration.os.geteuid", return_value=0):
            self.assertEqual(unintegrate(), 1)

        self.assertTrue(desktop_path.is_file())

    def test_unintegrate_removes_only_managed_files(self) -> None:
        self.assertEqual(integrate(appdir=self.appdir), 0)

        self.assertEqual(unintegrate(), 0)
        self.assertFalse(
            (self.data_home / "applications" / "xlauncher-appimage.desktop").exists()
        )
        self.assertFalse(
            (
                self.data_home
                / "icons"
                / "hicolor"
                / "scalable"
                / "apps"
                / "xlauncher-appimage.svg"
            ).exists()
        )


if __name__ == "__main__":
    unittest.main()
