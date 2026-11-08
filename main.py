import argparse
import sys
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gdk, GLib, Gtk, Pango

from alias_manager import Alias, load_aliases, resolve_alias
from app_launcher import ApplicationLaunchError, launch_application
from calculator import CalculationError, CalculationResult, calculate
from desktop_parser import DesktopApplication, load_desktop_applications
from fuzzy_search import search_applications
from history_manager import load_history_ids, record_application
from toggle_daemon import ToggleServer, control_daemon
from web_search import WebSearchResult, open_web_search, open_web_uri


STYLESHEET = """
window.launcher-window {
  background-color: transparent;
}

.launcher-surface {
  background-color: #000000;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
}

entry.launcher-entry {
  min-height: 32px;
  padding: 12px 18px;
  border: none;
  border-radius: 12px;
  background-color: transparent;
  background-image: none;
  box-shadow: none;
  color: #ffffff;
  caret-color: #ffffff;
  font-family: "SF Pro Display", sans-serif;
  font-size: 16pt;
}

entry.launcher-entry:focus {
  outline: none;
  box-shadow: none;
}

listbox.launcher-results,
listbox.launcher-results row {
  background-color: transparent;
  color: #ffffff;
}

listbox.launcher-results row {
  min-height: 48px;
  padding: 4px 14px;
  border-radius: 8px;
}

listbox.launcher-results row:selected {
  background-color: #252525;
}

.launcher-description,
.launcher-status {
  color: #aaaaaa;
  font-size: 10pt;
}

.launcher-status {
  padding: 0 18px 8px;
}
"""


class XLauncher(Gtk.Application):
    def __init__(self, daemon_mode: bool = False) -> None:
        super().__init__(application_id="org.example.XLauncher")
        self.daemon_mode = daemon_mode
        self.window: Gtk.ApplicationWindow | None = None
        self.entry: Gtk.Entry | None = None
        self.results_list: Gtk.ListBox | None = None
        self.status_label: Gtk.Label | None = None
        self.results: list[
            DesktopApplication | CalculationResult | WebSearchResult | Alias
        ] = []
        self.applications = load_desktop_applications()
        self.aliases = load_aliases()
        self.history_ids = load_history_ids()
        self.control_server: ToggleServer | None = None

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        if self.daemon_mode:
            self.hold()
            self.control_server = ToggleServer(self._handle_control)
            self.control_server.start()

    def do_activate(self) -> None:
        if not self.daemon_mode:
            self._show_launcher()

    def do_shutdown(self) -> None:
        if self.control_server is not None:
            self.control_server.stop()
            self.control_server = None
        Gtk.Application.do_shutdown(self)

    def _create_window(self) -> Gtk.ApplicationWindow:
        display = Gdk.Display.get_default()
        if display is None:
            raise RuntimeError("GTK could not connect to a display.")

        provider = Gtk.CssProvider()
        provider.load_from_data(STYLESHEET.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        window = Gtk.ApplicationWindow(application=self)
        window.set_title("X-Launcher")
        window.set_default_size(600, 60)
        window.set_resizable(False)
        window.set_decorated(False)
        window.add_css_class("launcher-window")
        window.connect("close-request", self._on_close_request)

        surface = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        surface.add_css_class("launcher-surface")

        entry = Gtk.Entry()
        entry.add_css_class("launcher-entry")
        entry.set_placeholder_text("Uygulama ara")
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
        self._set_status("")
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
        stripped_query = query.lstrip()
        alias = resolve_alias(query, self.aliases)
        if alias is not None:
            if alias.kind == "app":
                application = next(
                    (
                        item
                        for item in self.applications
                        if item.desktop_id == alias.value
                    ),
                    None,
                )
                self.results = [application] if application is not None else []
                self._set_status(
                    ""
                    if application is not None
                    else f"Takma adın uygulaması bulunamadı: {alias.value}"
                )
            else:
                self.results = [alias]
                self._set_status("")
            self._populate_results()
            return

        if stripped_query.startswith("="):
            expression = stripped_query[1:].strip()
            if not expression:
                self.results = []
                self._populate_results()
                self._set_status("")
                return
            try:
                self.results = [calculate(expression)]
                self._set_status("")
            except CalculationError as error:
                self.results = []
                self._set_status(str(error))
            self._populate_results()
            return

        if stripped_query.casefold().startswith("g "):
            search_query = stripped_query[2:].strip()
            if search_query:
                self.results = [WebSearchResult(search_query)]
                self._set_status("")
            else:
                self.results = []
                self._set_status("Google'da aramak için bir ifade yaz.")
            self._populate_results()
            return

        self.results = search_applications(
            self.applications, query, history_ids=self.history_ids
        )
        self._populate_results()
        self._set_status(
            ""
            if self.results
            else ("Uygulama bulunamadı" if query.strip() else "")
        )

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
                title = f"Google'da ara: {application.query}"
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
            else:
                if application.icon is not None:
                    image = Gtk.Image.new_from_gicon(application.icon)
                    image.set_pixel_size(28)
                    row_content.append(image)
                title = application.name
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
        _ = controller, keycode, state
        if keyval == Gdk.KEY_Escape:
            self._hide_launcher()
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
            else:
                self._launch_application(result)

    def _copy_calculation_result(self, result: CalculationResult) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            self._set_status("Pano kullanılamıyor.")
            return
        provider = Gdk.ContentProvider.new_for_value(result.display_value)
        if not display.get_clipboard().set_content(provider):
            self._set_status("Sonuç panoya kopyalanamadı.")
            return
        self._set_status(f"{result.display_value} panoya kopyalandı.")

    def _open_web_search(self, result: WebSearchResult) -> None:
        try:
            open_web_search(result.query)
        except (GLib.Error, OSError, RuntimeError, ValueError) as error:
            self._set_status(f"Web araması açılamadı: {error}")
            return
        self._hide_launcher()

    def _open_alias(self, alias: Alias) -> None:
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
        record_application(application.desktop_id)
        self.history_ids = [
            application.desktop_id,
            *(
                desktop_id
                for desktop_id in self.history_ids
                if desktop_id != application.desktop_id
            ),
        ][:20]
        self._hide_launcher()


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv if argv is None else argv)
    parser = argparse.ArgumentParser(description="GTK4 application launcher")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--daemon", action="store_true", help="run as a background launcher daemon")
    mode.add_argument("--toggle", action="store_true", help="toggle the daemon's launcher window")
    mode.add_argument("--stop", action="store_true", help="stop the launcher daemon")
    options = parser.parse_args(arguments[1:])

    if options.toggle or options.stop:
        command = "stop" if options.stop else "toggle"
        return control_daemon(command, Path(__file__).resolve())

    app = XLauncher(daemon_mode=options.daemon)
    return app.run([arguments[0]])


if __name__ == "__main__":
    raise SystemExit(main())
