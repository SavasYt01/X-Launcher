"""Discover installed desktop applications through the freedesktop app database."""

import gi

gi.require_version("Gio", "2.0")
gi.require_version("GioUnix", "2.0")
from gi.repository import Gio, GioUnix


class DesktopApplication:
    def __init__(self, app_info: GioUnix.DesktopAppInfo) -> None:
        self.app_info = app_info
        self.desktop_id = app_info.get_id() or ""
        self.name = app_info.get_display_name() or self.desktop_id
        self.executable = app_info.get_executable() or ""
        self.comment = app_info.get_description() or ""
        self.icon = app_info.get_icon()


def load_desktop_applications() -> list[DesktopApplication]:
    """Return visible desktop entries, respecting XDG lookup and override rules."""
    applications: list[DesktopApplication] = []
    for app_info in Gio.AppInfo.get_all():
        if not isinstance(app_info, GioUnix.DesktopAppInfo) or not app_info.should_show():
            continue
        application = DesktopApplication(app_info)
        if application.name:
            applications.append(application)
    return sorted(applications, key=lambda app: app.name.casefold())
