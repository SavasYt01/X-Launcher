import contextlib
import io
import unittest

from launcher_cli import dispatch


class LauncherCliTests(unittest.TestCase):
    def test_help_is_turkish_and_does_not_start_gtk(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = dispatch(["--help"])

        self.assertEqual(result, 0)
        self.assertIn("GTK4 Linux uygulama başlatıcısı", output.getvalue())
        self.assertIn("--doctor", output.getvalue())
        self.assertNotIn("GTK4 application launcher", output.getvalue())

    def test_version_matches_application_metadata(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = dispatch(["--version"])

        self.assertEqual(result, 0)
        self.assertIn("1.2.0", output.getvalue())

    def test_doctor_runs_without_opening_a_window(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = dispatch(["--doctor"])

        self.assertEqual(result, 0, output.getvalue())
        self.assertIn("ağ bağlantısı kullanılmaz", output.getvalue())

    def test_gui_arguments_are_delegated_to_gtk_application(self) -> None:
        self.assertIsNone(dispatch(["--toggle"]))


if __name__ == "__main__":
    unittest.main()
