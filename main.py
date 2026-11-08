import argparse
import logging
import sys
import threading
import time
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gio", "2.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango

from alias_manager import Alias, load_aliases, resolve_alias
from app_launch_context import create_app_launch_context
from app_launcher import ApplicationLaunchError, launch_application
from calculator import CalculationError, CalculationResult, calculate
from clipboard_history import (
    ClipboardEntry,
    clear_clipboard_history,
    load_clipboard_history,
    record_clipboard_text,
)
from command_router import route_query
from config_manager import ConfigManager
from desktop_parser import DesktopApplication, load_desktop_applications
from file_search import (
    FileSearchResult,
    index_home_files,
    resolve_home_path,
    search_files,
)
from favorites_manager import FavoritesManager
from fuzzy_search import search_applications
from help_content import HELP_ENTRIES, QUICK_HELP_ENTRIES, HelpEntry
from history_manager import history_scores, load_history_ids, record_application
from preferences_window import PreferencesWindow
from providers import ProviderResult
from theme_manager import load_theme
from toggle_daemon import ToggleServer, control_daemon
from version import APP_ID, APP_NAME, VERSION
from web_search import WebSearchResult, open_engine_search, open_web_uri


LOGGER = logging.getLogger(__name__)


class XLauncher(Gtk.Application):
    def __init__(self, daemon_mode: bool = False) -> None:
        super().__init__(application_id=APP_ID)
        self.daemon_mode = daemon_mode
        self.window: Gtk.ApplicationWindow | None = None
        self.preferences_window: PreferencesWindow | None = None
        self.entry: Gtk.Entry | None = None
        self.results_list: Gtk.ListBox | None = None
        self.status_label: Gtk.Label | None = None
        self.results: list[
            DesktopApplication
            | CalculationResult
            | WebSearchResult
            | Alias
            | ClipboardEntry
            | ProviderResult
            | HelpEntry
            | FileSearchResult
        ] = []
        self.config = ConfigManager()
        self.favorites_manager = FavoritesManager()
        self.applications: list[DesktopApplication] = []
        self.aliases = load_aliases()
        self.history_ids = load_history_ids()
        self.favorite_ids = self.favorites_manager.load()
        theme = load_theme()
        self.theme_css = theme.css
        self.theme_warning = theme.warning or self.config.warning
        self.css_provider: Gtk.CssProvider | None = None
        self.control_server: ToggleServer | None = None
        self._refresh_lock = threading.Lock()
        self._refresh_generation = 0
        self._last_refresh = time.monotonic()
        self._file_signatures: dict[str, tuple[int, int, int] | None] = {}
        self._watch_source_id = 0
        self._file_scan_lock = threading.Lock()
        self.file_index: tuple[Path, ...] = ()
        self._file_index_ready = False

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        if self.daemon_mode:
            self.hold()
            self.control_server = ToggleServer(self._handle_control)
            self.control_server.start()
        self._remember_file_signatures()
        self._watch_source_id = GLib.timeout_add_seconds(1, self._watch_user_files)
        self._start_application_refresh()
        self._start_file_index_refresh()

    def do_activate(self) -> None:
        if not self.daemon_mode:
            self._show_launcher()

    def do_shutdown(self) -> None:
        if self.control_server is not None:
            self.control_server.stop()
            self.control_server = None
        if self._watch_source_id:
            GLib.source_remove(self._watch_source_id)
            self._watch_source_id = 0
        Gtk.Application.do_shutdown(self)

    def _create_window(self) -> Gtk.ApplicationWindow:
        display = Gdk.Display.get_default()
        if display is None:
            raise RuntimeError("GTK could not connect to a display.")

        provider = Gtk.CssProvider()
        provider.load_from_string(self.theme_css)
        self.css_provider = provider
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        window = Gtk.ApplicationWindow(application=self)
        window.set_title(APP_NAME)
        window.set_default_size(600, 60)
        window.set_resizable(False)
        window.set_decorated(False)
        window.add_css_class("launcher-window")
        window.connect("close-request", self._on_close_request)

        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        surface.add_css_class("launcher-surface")

        entry = Gtk.Entry()
        entry.add_css_class("launcher-entry")
        entry.set_placeholder_text("Uygulama ara · 5*3 hesapla · f dosya · help")
        entry.set_hexpand(True)
        entry.connect("changed", self._on_search_changed)
        entry.connect("activate", self._launch_selected)
        surface.append(entry)
        self.entry = entry

        results = Gtk.ListBox()
        results.add_css_class("launcher-results")
        results.set_selection_mode(Gtk.SelectionMode.SINGLE)
        results.set_activate_on_single_click(False)
        results.connect("row-activated", self._on_row_activated)
        results.set_visible(False)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_max_content_height(320)
        scroller.set_propagate_natural_height(True)
        scroller.set_child(results)
        surface.append(scroller)
        self.results_list = results

        status = Gtk.Label(xalign=0)
        status.add_css_class("launcher-status")
        status.set_wrap(True)
        status.set_visible(False)
        surface.append(status)
        self.status_label = status

        window.set_child(surface)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        window.add_controller(key_controller)
        return window

    def _show_launcher(self) -> None:
        if self.window is None:
            self.window = self._create_window()
        if self.entry is not None:
            self.entry.set_text("")
        self._set_status(self.theme_warning or "")
        self.window.present()
        if self.entry is not None:
            self.entry.grab_focus()

    def _hide_launcher(self) -> None:
        if self.entry is not None:
            self.entry.set_text("")
        self._set_status("")
        if self.window is not None:
            self.window.set_visible(False)

    def _toggle_launcher(self) -> None:
        if self.window is not None and self.window.get_visible():
            self._hide_launcher()
        else:
            self._show_launcher()

    def _handle_control(self, command: str) -> bool:
        if command == "toggle":
            self._toggle_launcher()
        elif command == "stop":
            self.quit()
        elif command == "reload-apps":
            self._start_application_refresh()
        elif command == "reload":
            self._reload_user_files()
            self._start_application_refresh()
            self._start_file_index_refresh()
        return GLib.SOURCE_REMOVE

    def _on_close_request(self, window: Gtk.ApplicationWindow) -> bool:
        if window is not self.window:
            return False
        self._hide_launcher()
        return True

    def _on_search_changed(self, entry: Gtk.Entry) -> None:
        if self.results_list is None:
            return
        query = entry.get_text()
        route = route_query(
            query,
            alias=resolve_alias(query, self.aliases),
            default_engine=self.config.values["search_engine"],
        )
        self._set_status("")
        if route.kind == "empty":
            self.results = self._empty_query_results()
        elif route.kind == "help":
            self.results = list(HELP_ENTRIES)
        elif route.kind == "alias":
            alias = route.value
            if alias.kind == "app":
                application = next(
                    (app for app in self.applications if app.desktop_id == alias.value),
                    None,
                )
                self.results = [application] if application is not None else []
                if application is None:
                    self._set_status(f"Takma adın uygulaması bulunamadı: {alias.value}")
            else:
                self.results = [alias]
        elif route.kind == "calculator":
            try:
                self.results = [calculate(route.value)]
            except CalculationError as error:
                self.results = []
                self._set_status(str(error))
        elif route.kind == "file_search":
            if not route.value:
                self.results = []
                self._set_status("Dosya aramak için bir ifade yazın.")
            elif not self._file_index_ready:
                self.results = []
                self._set_status("Dosyalar taranıyor...")
            else:
                self.results = search_files(
                    route.value,
                    self.file_index,
                    limit=self.config.values["result_limit"],
                )
                if not self.results:
                    self._set_status("Dosya veya klasör bulunamadı.")
        elif route.kind == "web_search":
            search_query, engine = route.value
            self.results = [WebSearchResult(search_query, engine)]
        elif route.kind == "clipboard":
            if route.value == "clear":
                self._confirm_clear_clipboard()
                self.results = []
            elif self.config.values["clipboard_history_enabled"]:
                self.results = load_clipboard_history()
                if not self.results:
                    self._set_status("Pano geçmişi boş.")
            else:
                self.results = []
                self._set_status("Pano geçmişi devre dışı.")
        elif route.kind == "provider":
            result = route.value
            self.results = [] if result.kind == "error" else [result]
            if result.kind == "error":
                self._set_status(result.description)
        elif route.kind == "error":
            self.results = []
            self._set_status(route.value)
        else:
            scores = history_scores(base_boost=self.config.values["history_boost"])
            self.results = search_applications(
                self.applications,
                route.value,
                limit=self.config.values["result_limit"],
                history_ids=(
                    self.history_ids if self.config.values["show_recent"] else []
                ),
                history_scores=(
                    scores if self.config.values["show_recent"] else {}
                ),
                favorite_ids=(
                    self.favorite_ids if self.config.values["show_favorites"] else []
                ),
            )
        self._populate_results()
        if route.kind == "applications" and query.strip() and not self.results:
            self._set_status("Uygulama bulunamadı.")

    def _empty_query_results(
        self,
    ) -> list[DesktopApplication | HelpEntry]:
        favorites = (
            self.favorite_ids
            if self.config.values["show_favorites_on_empty"]
            and self.config.values["show_favorites"]
            else []
        )
        recent = (
            self.history_ids
            if self.config.values["show_recent_on_empty"]
            and self.config.values["show_recent"]
            else []
        )
        by_id = {app.desktop_id: app for app in self.applications}
        ordered_ids = dict.fromkeys([*favorites, *recent])
        applications = [
            by_id[desktop_id]
            for desktop_id in ordered_ids
            if desktop_id in by_id
        ]
        return [
            *QUICK_HELP_ENTRIES,
            *applications,
        ][: self.config.values["result_limit"]]

    def _populate_results(self) -> None:
        if self.results_list is None:
            return
        row = self.results_list.get_first_child()
        while row is not None:
            next_row = row.get_next_sibling()
            self.results_list.remove(row)
            row = next_row

        for application in self.results:
            row_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            if isinstance(application, CalculationResult):
                image = Gtk.Image.new_from_icon_name("accessories-calculator-symbolic")
                image.set_pixel_size(28)
                row_content.append(image)
                title = f"= {application.display_value}"
                description_text = f"{application.expression}  ·  Enter ile panoya kopyala"
            elif isinstance(application, WebSearchResult):
                image = Gtk.Image.new_from_icon_name("web-browser-symbolic")
                image.set_pixel_size(28)
                row_content.append(image)
                title = f"{application.engine} üzerinde ara: {application.query}"
                description_text = "Enter ile varsayılan tarayıcıda ara"
            elif isinstance(application, Alias):
                icon_name = (
                    "web-browser-symbolic"
                    if application.kind == "web"
                    else "system-run-symbolic"
                )
                image = Gtk.Image.new_from_icon_name(icon_name)
                image.set_pixel_size(28)
                row_content.append(image)
                title = f"{application.key} → {application.value}"
                description_text = "Takma ad ile web adresi aç"
            elif isinstance(application, ClipboardEntry):
                image = Gtk.Image.new_from_icon_name("edit-paste-symbolic")
                image.set_pixel_size(28)
                row_content.append(image)
                title = application.text.splitlines()[0][:100]
                description_text = application.timestamp
            elif isinstance(application, ProviderResult):
                image = Gtk.Image.new_from_icon_name("accessories-calculator-symbolic")
                image.set_pixel_size(28)
                row_content.append(image)
                title = application.title
                description_text = application.description
            elif isinstance(application, HelpEntry):
                image = Gtk.Image.new_from_icon_name("help-about-symbolic")
                image.set_pixel_size(28)
                row_content.append(image)
                title = application.title
                description_text = application.description
            elif isinstance(application, FileSearchResult):
                icon_name = (
                    "folder-symbolic"
                    if application.path.is_dir()
                    else "text-x-generic-symbolic"
                )
                image = Gtk.Image.new_from_icon_name(icon_name)
                image.set_pixel_size(28)
                row_content.append(image)
                title = application.name
                description_text = application.description
            else:
                image = Gtk.Image.new_from_icon_name("application-x-executable")
                if application.icon is not None:
                    image.set_from_gicon(application.icon)
                image.set_pixel_size(28)
                row_content.append(image)
                favorite_marker = "★ " if application.desktop_id in self.favorite_ids else ""
                title = f"{favorite_marker}{application.name}"
                description_text = application.comment

            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            name = Gtk.Label(label=title, xalign=0)
            name.set_ellipsize(Pango.EllipsizeMode.END)
            labels.append(name)
            if description_text:
                description = Gtk.Label(label=description_text, xalign=0)
                description.add_css_class("launcher-description")
                description.set_ellipsize(Pango.EllipsizeMode.END)
                labels.append(description)
            row_content.append(labels)

            row = Gtk.ListBoxRow()
            row.set_child(row_content)
            self.results_list.append(row)

        self.results_list.set_visible(bool(self.results))
        first_row = self.results_list.get_row_at_index(0)
        if first_row is not None:
            self.results_list.select_row(first_row)

    def _set_status(self, message: str) -> None:
        if self.status_label is not None:
            self.status_label.set_text(message)
            self.status_label.set_visible(bool(message))

    def _on_key_pressed(
        self,
        controller: Gtk.EventControllerKey,
        keyval: int,
        keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        _ = controller, keycode
        if keyval == Gdk.KEY_Escape:
            self._hide_launcher()
            return True
        if state & Gdk.ModifierType.CONTROL_MASK:
            if keyval in (Gdk.KEY_r, Gdk.KEY_R):
                self._start_application_refresh()
                self._start_file_index_refresh()
                return True
            if keyval == Gdk.KEY_comma:
                self._show_preferences()
                return True
            if keyval in (Gdk.KEY_d, Gdk.KEY_D):
                return self._toggle_favorite()
            if keyval in (Gdk.KEY_l, Gdk.KEY_L):
                if self.entry is not None:
                    self.entry.set_text("")
                    self.entry.grab_focus()
                return True
        if keyval in (Gdk.KEY_Up, Gdk.KEY_Down):
            return self._move_selection(-1 if keyval == Gdk.KEY_Up else 1)
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._launch_selected()
            return True
        return False

    def _move_selection(self, step: int) -> bool:
        if self.results_list is None or not self.results:
            return False
        row = self.results_list.get_selected_row()
        current_index = row.get_index() if row is not None else 0
        next_index = max(0, min(len(self.results) - 1, current_index + step))
        next_row = self.results_list.get_row_at_index(next_index)
        if next_row is not None:
            self.results_list.select_row(next_row)
        return True

    def _on_row_activated(
        self,
        list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow,
    ) -> None:
        if list_box is not self.results_list:
            return
        index = row.get_index()
        if 0 <= index < len(self.results):
            result = self.results[index]
            if isinstance(result, CalculationResult):
                self._copy_calculation_result(result)
            elif isinstance(result, WebSearchResult):
                self._open_web_search(result)
            elif isinstance(result, Alias):
                self._open_alias(result)
            elif isinstance(result, ClipboardEntry):
                self._copy_text(result.text)
            elif isinstance(result, ProviderResult):
                if result.value:
                    self._copy_text(result.value)
            elif isinstance(result, HelpEntry):
                return
            elif isinstance(result, FileSearchResult):
                self._open_file(result)
            else:
                self._launch_application(result)

    def _copy_calculation_result(self, result: CalculationResult) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            self._set_status("Pano kullanılamıyor.")
            return
        try:
            display.get_clipboard().set_text(result.display_value)
        except (GLib.Error, RuntimeError, TypeError) as error:
            self._set_status(f"Sonuç panoya kopyalanamadı: {error}")
            return
        if not self._record_clipboard_text(result.display_value):
            LOGGER.warning("Hesaplama sonucu pano geçmişine kaydedilemedi.")
        self._set_status(f"{result.display_value} panoya kopyalandı.")

    def _record_clipboard_text(self, text: str) -> bool:
        if not self.config.values["clipboard_history_enabled"]:
            return True
        return record_clipboard_text(
            text,
            limit=self.config.values["max_clipboard_history"],
            enabled=True,
        )

    def _copy_text(self, text: str) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            self._set_status("Pano kullanılamıyor.")
            return
        try:
            display.get_clipboard().set_text(text)
        except (GLib.Error, RuntimeError, TypeError) as error:
            self._set_status(f"Metin panoya kopyalanamadı: {error}")
            return
        if not self._record_clipboard_text(text):
            LOGGER.warning("Metin pano geçmişine kaydedilemedi.")
        self._set_status("Metin panoya kopyalandı.")

    def _open_web_search(self, result: WebSearchResult) -> None:
        try:
            open_engine_search(result.query, result.engine)
        except (GLib.Error, OSError, RuntimeError, ValueError) as error:
            self._set_status(f"Web araması açılamadı: {error}")
            return
        self._hide_launcher()

    def _open_file(self, result: FileSearchResult) -> None:
        try:
            path = resolve_home_path(result.path)
            launched = Gio.AppInfo.launch_default_for_uri(
                path.as_uri(),
                create_app_launch_context(),
            )
        except (GLib.Error, OSError, RuntimeError, ValueError) as error:
            self._set_status(f"Dosya açılamadı: {error}")
            return
        if not launched:
            self._set_status("Dosya varsayılan uygulamayla açılamadı.")
            return
        self._hide_launcher()

    def _open_alias(self, alias: Alias) -> None:
        if alias.kind == "app":
            application = next(
                (app for app in self.applications if app.desktop_id == alias.value),
                None,
            )
            if application is None:
                self._set_status(f"Takma adın uygulaması bulunamadı: {alias.value}")
                return
            self._launch_application(application)
            return
        try:
            open_web_uri(alias.value)
        except (GLib.Error, OSError, RuntimeError, ValueError) as error:
            self._set_status(f"Takma ad açılamadı: {error}")
            return
        self._hide_launcher()

    def _launch_selected(self, *args: object) -> None:
        _ = args
        if self.results_list is None:
            return
        row = self.results_list.get_selected_row()
        if row is not None:
            self._on_row_activated(self.results_list, row)

    def _launch_application(self, application: DesktopApplication) -> None:
        try:
            launch_application(application)
        except (ApplicationLaunchError, GLib.Error, OSError, RuntimeError, TypeError) as error:
            self._set_status(f"{application.name} başlatılamadı: {error}")
            return
        if not record_application(
            application.desktop_id,
            max_history=self.config.values["max_history"],
        ):
            LOGGER.warning("Uygulama geçmişine kayıt yapılamadı: %s", application.desktop_id)
        self.history_ids = [
            application.desktop_id,
            *(desktop_id for desktop_id in self.history_ids if desktop_id != application.desktop_id),
        ][: self.config.values["max_history"]]
        self._hide_launcher()

    def _confirm_clear_clipboard(self) -> None:
        if self.window is None:
            return
        dialog = Gtk.Window(title="Pano geçmişini temizle?", transient_for=self.window, modal=True)
        dialog.set_default_size(320, 120)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.append(Gtk.Label(label="Bu işlem geri alınamaz.", xalign=0))
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cancel = Gtk.Button(label="Vazgeç")

        def cancel_clear(button: Gtk.Button) -> None:
            _ = button
            dialog.close()

        cancel.connect("clicked", cancel_clear)
        confirm = Gtk.Button(label="Temizle")

        def clear(button: Gtk.Button) -> None:
            _ = button
            if clear_clipboard_history():
                self._set_status("Pano geçmişi temizlendi.")
            else:
                self._set_status("Pano geçmişi temizlenemedi.")
            dialog.close()

        confirm.connect("clicked", clear)
        buttons.append(cancel)
        buttons.append(confirm)
        content.append(buttons)
        dialog.set_child(content)
        dialog.present()

    def _installed_ids(self) -> set[str]:
        return {application.desktop_id for application in self.applications}

    def _toggle_favorite(self) -> bool:
        if self.results_list is None:
            return False
        row = self.results_list.get_selected_row()
        if row is None:
            return False
        result = self.results[row.get_index()]
        if not isinstance(result, DesktopApplication):
            return False
        if not self.favorites_manager.toggle(result.desktop_id, self._installed_ids()):
            self._set_status("Favori değiştirilemedi.")
            return True
        self.favorite_ids = self.favorites_manager.load(self._installed_ids())
        self._set_status(
            "Favorilere eklendi."
            if result.desktop_id in self.favorite_ids
            else "Favorilerden kaldırıldı."
        )
        self._on_search_changed(self.entry) if self.entry is not None else None
        return True

    def _show_preferences(self) -> None:
        if self.window is None:
            return
        if self.preferences_window is not None:
            self.preferences_window.present()
            return
        self.preferences_window = PreferencesWindow(
            self.window,
            self.config,
            self.applications,
            self._reload_user_files,
        )
        self.preferences_window.connect(
            "close-request",
            self._on_preferences_close_request,
        )
        self.preferences_window.present()

    def _on_preferences_close_request(self, window: Gtk.Window) -> bool:
        if self.preferences_window is window:
            self.preferences_window = None
        return False

    def _reload_user_files(self) -> None:
        self.config.load()
        self.aliases = load_aliases(fallback=self.aliases)
        self.favorite_ids = self.favorites_manager.load(self._installed_ids())
        self.history_ids = load_history_ids()
        theme = load_theme()
        self.theme_css = theme.css
        self.theme_warning = theme.warning or self.config.warning
        if self.css_provider is not None:
            self.css_provider.load_from_string(self.theme_css)
        self._remember_file_signatures()
        if self.entry is not None:
            self._on_search_changed(self.entry)

    def _user_files(self) -> dict[str, Path]:
        data_dir = self.config.path.parent
        theme_name = self.config.values["active_theme"]
        return {
            "config": self.config.path,
            "aliases": data_dir / "aliases.json",
            "favorites": data_dir / "favorites.json",
            "history": data_dir / "history.json",
            "clipboard": data_dir / "clipboard_history.json",
            "user-theme": data_dir / "themes" / theme_name / "theme.css",
            "bundled-theme": (
                Path(__file__).resolve().parent
                / "themes"
                / theme_name
                / "theme.css"
            ),
        }

    def _file_signature(self, path: Path) -> tuple[int, int, int] | None:
        try:
            info = path.stat()
        except FileNotFoundError:
            return None
        except OSError:
            LOGGER.exception("Kullanıcı dosyası izlenemedi: %s", path)
            return None
        return info.st_mtime_ns, info.st_size, info.st_ino

    def _remember_file_signatures(self) -> None:
        self._file_signatures = {
            key: self._file_signature(path) for key, path in self._user_files().items()
        }

    def _watch_user_files(self) -> bool:
        current = {
            key: self._file_signature(path) for key, path in self._user_files().items()
        }
        if current != self._file_signatures:
            self._file_signatures = current
            self._reload_user_files()

        interval = self.config.values["refresh_interval_seconds"]
        if interval and time.monotonic() - self._last_refresh >= interval:
            self._start_application_refresh()
        return GLib.SOURCE_CONTINUE

    def _start_application_refresh(self) -> None:
        if not self._refresh_lock.acquire(blocking=False):
            return
        self._refresh_generation += 1
        generation = self._refresh_generation
        if self.status_label is not None:
            self._set_status("Uygulamalar taranıyor...")

        def scan() -> None:
            try:
                applications = load_desktop_applications()
                error = None
            except (
                GLib.Error,
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
            ) as caught_error:
                LOGGER.exception("Uygulamalar yenilenemedi.")
                applications = None
                error = caught_error
            GLib.idle_add(self._finish_application_refresh, generation, applications, error)

        threading.Thread(target=scan, name="xlauncher-app-scan", daemon=True).start()

    def _start_file_index_refresh(self) -> None:
        if not self._file_scan_lock.acquire(blocking=False):
            return
        if self._is_file_search_query():
            self._set_status("Dosyalar taranıyor...")

        def scan() -> None:
            try:
                indexed_paths = index_home_files()
                error = None
            except (OSError, RuntimeError, ValueError) as caught_error:
                LOGGER.exception("Kullanıcı dosyaları taranamadı.")
                indexed_paths = None
                error = caught_error
            GLib.idle_add(
                self._finish_file_index_refresh,
                indexed_paths,
                error,
            )

        threading.Thread(target=scan, name="xlauncher-file-scan", daemon=True).start()

    def _is_file_search_query(self) -> bool:
        return (
            self.entry is not None
            and route_query(self.entry.get_text()).kind == "file_search"
        )

    def _finish_file_index_refresh(
        self,
        indexed_paths: tuple[Path, ...] | None,
        error: Exception | None,
    ) -> bool:
        self._file_scan_lock.release()
        if error is not None or indexed_paths is None:
            if self._is_file_search_query():
                self._set_status(f"Dosyalar taranamadı: {error}")
            return GLib.SOURCE_REMOVE

        self.file_index = indexed_paths
        self._file_index_ready = True
        if self._is_file_search_query() and self.entry is not None:
            self._on_search_changed(self.entry)
        return GLib.SOURCE_REMOVE

    def _finish_application_refresh(
        self,
        generation: int,
        applications: list[DesktopApplication] | None,
        error: Exception | None,
    ) -> bool:
        self._refresh_lock.release()
        if generation != self._refresh_generation:
            return GLib.SOURCE_REMOVE
        if error is not None or applications is None:
            self._set_status(f"Uygulamalar yenilenemedi: {error}")
            return GLib.SOURCE_REMOVE
        self.applications = applications
        self.favorite_ids = self.favorites_manager.load(self._installed_ids())
        self._last_refresh = time.monotonic()
        if self.entry is not None:
            self._on_search_changed(self.entry)
        elif self.window is not None:
            self._set_status("Uygulamalar yenilendi.")
        return GLib.SOURCE_REMOVE


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(description="GTK4 Linux uygulama başlatıcısı")
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--daemon", action="store_true", help="arka plan daemon'ı olarak çalıştır")
    mode.add_argument("--toggle", action="store_true", help="başlatıcı penceresini aç veya gizle")
    mode.add_argument("--stop", action="store_true", help="başlatıcı daemon'ını durdur")
    mode.add_argument("--reload", action="store_true", help="ayarları ve uygulamaları yenile")
    mode.add_argument("--reload-apps", action="store_true", help="kurulu uygulamaları yeniden tara")
    options = parser.parse_args(arguments[1:])

    if options.toggle or options.stop or options.reload or options.reload_apps:
        command = (
            "stop"
            if options.stop
            else "reload"
            if options.reload
            else "reload-apps"
            if options.reload_apps
            else "toggle"
        )
        return control_daemon(command, Path(__file__).resolve())

    app = XLauncher(daemon_mode=options.daemon)
    return app.run([arguments[0]])


if __name__ == "__main__":
    raise SystemExit(main())
