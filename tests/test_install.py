import os
import subprocess
import tempfile
import unittest
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


class InstallScriptTests(unittest.TestCase):
    def test_installs_user_launcher_with_paths_containing_spaces(self) -> None:
        with tempfile.TemporaryDirectory(prefix="xlauncher install ") as temporary:
            root = Path(temporary)
            home = root / "home with spaces"
            data_home = home / ".local" / "share"
            bin_dir = home / ".local" / "bin"
            environment = os.environ.copy()
            environment.update(
                {
                    "HOME": str(home),
                    "XDG_DATA_HOME": str(data_home),
                    "XLAUNCHER_BIN_DIR": str(bin_dir),
                }
            )

            install = subprocess.run(
                [str(PROJECT_DIR / "install.sh")],
                cwd=PROJECT_DIR,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(install.returncode, 0, install.stderr)

            application_dir = data_home / "applications"
            desktop_file = application_dir / "xlauncher.desktop"
            self.assertTrue((data_home / "xlauncher" / "main.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "xlauncher-toggle").is_file())
            self.assertTrue((data_home / "icons/hicolor/scalable/apps/xlauncher.svg").is_file())

            entry = desktop_file.read_text(encoding="utf-8")
            self.assertIn(f'Exec="{bin_dir}/xlauncher"', entry)

            launcher = subprocess.run(
                [str(bin_dir / "xlauncher"), "--help"],
                cwd=PROJECT_DIR,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(launcher.returncode, 0, launcher.stderr)
            self.assertIn("GTK4 application launcher", launcher.stdout)


if __name__ == "__main__":
    unittest.main()
