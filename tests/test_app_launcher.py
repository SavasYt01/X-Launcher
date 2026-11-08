import os
import unittest
from unittest.mock import patch

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GioUnix", "2.0")
from gi.repository import GLib

from app_launch_context import create_app_launch_context
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


class FakeLaunchContext:
    def __init__(self) -> None:
        self.environment: dict[str, str | None] = {}

    def setenv(self, name: str, value: str) -> None:
        self.environment[name] = value

    def unsetenv(self, name: str) -> None:
        self.environment[name] = None


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

    def test_appimage_launch_context_restores_host_environment(self) -> None:
        environment = {
            "XLAUNCHER_APPIMAGE_RUNTIME": "1",
            "APPDIR": "/bundle",
            "APPIMAGE": "/bundle/X-Launcher.AppImage",
            "LD_LIBRARY_PATH": "/host/lib",
            "PYTHONPATH": "/host/python",
            "PATH": "/host/bin",
            "XLAUNCHER_HOST_ENV_SET_LD_LIBRARY_PATH": "1",
            "XLAUNCHER_HOST_ENV_VALUE_LD_LIBRARY_PATH": "/host/lib",
            "XLAUNCHER_HOST_ENV_SET_PYTHONPATH": "1",
            "XLAUNCHER_HOST_ENV_VALUE_PYTHONPATH": "/host/python",
            "XLAUNCHER_HOST_ENV_SET_PATH": "1",
            "XLAUNCHER_HOST_ENV_VALUE_PATH": "/host/bin",
        }
        context = FakeLaunchContext()
        with patch.dict(os.environ, environment, clear=True):
            with patch("app_launch_context.Gio.AppLaunchContext", return_value=context):
                result = create_app_launch_context()

        self.assertIs(result, context)
        self.assertEqual(context.environment["LD_LIBRARY_PATH"], "/host/lib")
        self.assertEqual(context.environment["PYTHONPATH"], "/host/python")
        self.assertEqual(context.environment["PATH"], "/host/bin")
        self.assertIsNone(context.environment["GI_TYPELIB_PATH"])
        self.assertIsNone(context.environment["APPDIR"])
        self.assertIsNone(context.environment["APPIMAGE"])
        self.assertIsNone(
            context.environment["XLAUNCHER_HOST_ENV_VALUE_LD_LIBRARY_PATH"]
        )

    def test_native_launch_uses_default_context(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(create_app_launch_context())


if __name__ == "__main__":
    unittest.main()
