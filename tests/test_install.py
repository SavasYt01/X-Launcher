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
            self.assertTrue((data_home / "xlauncher" / "history_manager.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "alias_manager.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "theme_manager.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "file_search.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "config_manager.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "preferences_window.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "launcher_cli.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "app_launch_context.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "doctor.py").is_file())
            self.assertTrue((data_home / "xlauncher" / "help_content.py").is_file())
            self.assertTrue(
                (data_home / "xlauncher/themes/default-dark/theme.css").is_file()
            )
            self.assertTrue((data_home / "xlauncher" / "xlauncher-toggle").is_file())
            self.assertTrue((bin_dir / "xlauncher-uninstall").is_file())
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
            self.assertIn("GTK4 Linux uygulama başlatıcısı", launcher.stdout)
            doctor = subprocess.run(
                [str(bin_dir / "xlauncher"), "--doctor"],
                cwd=PROJECT_DIR,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
            self.assertIn("sistem tanılaması", doctor.stdout)

            settings = data_home / "xlauncher" / "config.json"
            history = data_home / "xlauncher" / "history.json"
            settings.write_text('{"active_theme":"nord"}\n', encoding="utf-8")
            history.write_text("[]\n", encoding="utf-8")
            custom_theme = data_home / "xlauncher" / "themes" / "nord" / "theme.css"
            custom_theme.parent.mkdir(parents=True)
            custom_theme.write_text("window { color: white; }\n", encoding="utf-8")
            uninstall = subprocess.run(
                [str(bin_dir / "xlauncher-uninstall")],
                cwd=PROJECT_DIR,
                env=environment,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(uninstall.returncode, 0, uninstall.stderr)
            self.assertFalse((data_home / "xlauncher" / "main.py").exists())
            self.assertFalse((data_home / "xlauncher" / "app_launch_context.py").exists())
            self.assertTrue(settings.is_file())
            self.assertTrue(history.is_file())
            self.assertTrue(custom_theme.is_file())
            self.assertFalse((bin_dir / "xlauncher").exists())


if __name__ == "__main__":
    unittest.main()
