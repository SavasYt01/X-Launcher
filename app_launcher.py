"""Launch applications using the desktop-entry implementation from GLib."""

import gi

gi.require_version("GioUnix", "2.0")
from gi.repository import GLib, GioUnix

from desktop_parser import DesktopApplication


class ApplicationLaunchError(RuntimeError):
    """Raised when GLib cannot launch a desktop application."""


def launch_application(application: DesktopApplication) -> None:
    """Launch a parsed desktop entry without invoking a shell."""
    if not isinstance(application.app_info, GioUnix.DesktopAppInfo):
        raise TypeError("The selected entry is not a launchable desktop application.")
    try:
        launched = application.app_info.launch([], None)
    except GLib.Error as error:
        raise ApplicationLaunchError(str(error)) from error
    if not launched:
        raise ApplicationLaunchError("Başlatma isteği başarısız oldu.")
