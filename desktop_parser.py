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
        self.generic_name = app_info.get_generic_name() or ""
        keywords = app_info.get_keywords() or []
        self.keywords = tuple(keyword for keyword in keywords if keyword)
        self.executable = app_info.get_executable() or ""
        self.comment = app_info.get_description() or ""
        categories = app_info.get_categories() or ""
        self.categories = tuple(
            category for category in categories.split(";") if category
        )
        self.icon = app_info.get_icon()


def _application_key(application: DesktopApplication) -> str:
    return application.desktop_id or application.name.casefold()


def load_desktop_applications() -> list[DesktopApplication]:
    """Return visible desktop entries, respecting XDG lookup and override rules."""
    applications: list[DesktopApplication] = []
    for app_info in Gio.AppInfo.get_all():
        if not isinstance(app_info, GioUnix.DesktopAppInfo) or not app_info.should_show():
            continue
        application = DesktopApplication(app_info)
        if application.name:
            applications.append(application)
    unique = {_application_key(application): application for application in applications}
    return sorted(unique.values(), key=lambda app: app.name.casefold())
