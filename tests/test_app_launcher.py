import unittest
from unittest.mock import patch

import gi

gi.require_version("GioUnix", "2.0")
from gi.repository import GLib

from app_launcher import ApplicationLaunchError, launch_application
from desktop_parser import DesktopApplication


class FakeDesktopAppInfo:
    def __init__(self, result: bool = True, error: GLib.Error | None = None) -> None:
        self.result = result
        self.error = error

    def launch(self, files: list[object], context: object | None) -> bool:
        _ = files, context
        if self.error is not None:
            raise self.error
        return self.result


class ApplicationLauncherTests(unittest.TestCase):
    def make_application(self, app_info: FakeDesktopAppInfo) -> DesktopApplication:
        application = object.__new__(DesktopApplication)
        application.app_info = app_info
        application.name = "Test App"
        return application

    def test_reports_false_launch_result(self) -> None:
        application = self.make_application(FakeDesktopAppInfo(result=False))

        with patch("app_launcher.GioUnix.DesktopAppInfo", FakeDesktopAppInfo):
            with self.assertRaisesRegex(
                ApplicationLaunchError, "Başlatma isteği başarısız oldu"
            ):
                launch_application(application)

    def test_wraps_glib_launch_error(self) -> None:
        glib_error = GLib.Error("simulated launch failure")
        application = self.make_application(FakeDesktopAppInfo(error=glib_error))

        with patch("app_launcher.GioUnix.DesktopAppInfo", FakeDesktopAppInfo):
            with self.assertRaises(ApplicationLaunchError) as raised:
                launch_application(application)

        self.assertIs(raised.exception.__cause__, glib_error)


if __name__ == "__main__":
    unittest.main()
