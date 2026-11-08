"""Functional GTK4 preferences window for X-Launcher."""

import os
from pathlib import Path
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from alias_manager import Alias, load_aliases, save_aliases
from config_manager import ConfigManager
from desktop_parser import DesktopApplication
from favorites_manager import FavoritesManager
from history_manager import load_history
from theme_manager import DEFAULT_THEME_CSS
from web_search import validate_web_uri


class PreferencesWindow(Gtk.Window):
    def __init__(
        self,
        parent: Gtk.Window,
        config: ConfigManager,
        applications: list[DesktopApplication],
        on_saved: Callable[[], None],
    ) -> None:
        super().__init__(title="X-Launcher Ayarları", transient_for=parent)
        self.set_modal(False)
        self.set_default_size(620, 680)
        self.connect("close-request", self._on_close_request)
        self.config = config
        self.applications = applications
        self.on_saved = on_saved
        self._confirmation_dialog: Gtk.Window | None = None
        self.favorites = FavoritesManager()
        self.aliases = load_aliases()
        self.app_ids = {application.desktop_id for application in applications}
        self._switches: dict[str, Gtk.Switch] = {}
        self._spins: dict[str, Gtk.SpinButton] = {}

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16)
        root.set_margin_bottom(16)
        root.set_margin_start(16)
        root.set_margin_end(16)
        self.set_child(root)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        scroller.set_child(body)
        root.append(scroller)

        self._add_section(body, "Genel")
        self._add_switch(body, "Son kullanılanları boş aramada göster", "show_recent_on_empty")
        self._add_switch(body, "Favorileri boş aramada göster", "show_favorites_on_empty")
        self._add_switch(body, "Geçmişe göre sonuçları öne çıkar", "show_recent")
        self._add_switch(body, "Favorileri aramada öne çıkar", "show_favorites")
        self._add_spin(body, "Sonuç sayısı", "result_limit", 3, 20, 1)
        self._add_spin(body, "Otomatik tarama aralığı (saniye, 0=kapalı)", "refresh_interval_seconds", 0, 3600, 10)
        self._add_spin(body, "Maksimum uygulama geçmişi", "max_history", 1, 200, 1)

        self._add_section(body, "Arama")
        self._add_spin(body, "Geçmiş sıralama katkısı", "history_boost", 0, 100, 5)
        self.engine_dropdown = Gtk.DropDown.new_from_strings(
            ["Google", "DuckDuckGo", "Brave Search"]
        )
        self.engine_dropdown.set_selected(
            {"google": 0, "duckduckgo": 1, "brave": 2}.get(
                config.values["search_engine"], 0
            )
        )
        self._add_control_row(body, "Varsayılan arama motoru", self.engine_dropdown)

        self._add_section(body, "Görünüm")
        theme_names = self._available_themes()
        self.theme_dropdown = Gtk.DropDown.new_from_strings(theme_names)
        current_theme = config.values["active_theme"]
        self.theme_dropdown.set_selected(
            theme_names.index(current_theme) if current_theme in theme_names else 0
        )
        self.theme_dropdown.connect("notify::selected", self._update_theme_preview)
        self._add_control_row(body, "Aktif tema", self.theme_dropdown)
        self.theme_preview = Gtk.TextView()
        self.theme_preview.set_editable(False)
        self.theme_preview.set_cursor_visible(False)
        self.theme_preview.set_monospace(True)
        self.theme_preview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        preview_scroll = Gtk.ScrolledWindow()
        preview_scroll.set_min_content_height(100)
        preview_scroll.set_child(self.theme_preview)
        body.append(preview_scroll)
        self._update_theme_preview()

        self._add_section(body, "Takma adlar")
        self.alias_list = Gtk.ListBox()
        self.alias_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        body.append(self.alias_list)
        self.alias_key = Gtk.Entry()
        self.alias_key.set_placeholder_text("Takma ad (örn. yt)")
        self.alias_value = Gtk.Entry()
        self.alias_value.set_placeholder_text("Desktop ID veya https:// adresi")
        self.alias_type = Gtk.DropDown.new_from_strings(["Uygulama", "Web adresi"])
        self._add_control_row(body, "Tür", self.alias_type)
        self._add_control_row(body, "Ad", self.alias_key)
        self._add_control_row(body, "Hedef", self.alias_value)
        alias_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_alias = Gtk.Button(label="Ekle / Güncelle")
        add_alias.connect("clicked", self._save_alias)
        remove_alias = Gtk.Button(label="Seçileni sil")
        remove_alias.connect("clicked", self._remove_alias)
        alias_buttons.append(add_alias)
        alias_buttons.append(remove_alias)
        body.append(alias_buttons)
        self._refresh_alias_list()

        self._add_section(body, "Geçmiş ve favoriler")
        self.history_list = Gtk.ListBox()
        self.history_list.set_selection_mode(Gtk.SelectionMode.NONE)
        body.append(self.history_list)
        clear_history = Gtk.Button(label="Uygulama geçmişini temizle")
        clear_history.connect("clicked", self._clear_app_history)
        body.append(clear_history)
        self.favorite_list = Gtk.ListBox()
        body.append(self.favorite_list)
        remove_favorite = Gtk.Button(label="Seçili favoriyi sil")
        remove_favorite.connect("clicked", self._remove_favorite)
        body.append(remove_favorite)
        self._refresh_user_data_lists()

        self._add_section(body, "Pano")
        self._add_switch(body, "X-Launcher kopyalama geçmişini etkinleştir", "clipboard_history_enabled")
        self._add_spin(body, "Maksimum pano kaydı", "max_clipboard_history", 1, 200, 1)
        clear_clipboard = Gtk.Button(label="Pano geçmişini temizle")
        clear_clipboard.connect("clicked", self._confirm_clear_clipboard)
        body.append(clear_clipboard)
        privacy = Gtk.Label(
            label="Yalnızca X-Launcher içinden açıkça kopyalanan metinler saklanır. "
            "Sistem panosu izlenmez. Bu veriler kullanıcıya özeldir.",
            xalign=0,
            wrap=True,
        )
        body.append(privacy)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        footer.set_halign(Gtk.Align.END)
        self.status = Gtk.Label(xalign=0)
        self.status.set_hexpand(True)
        footer.append(self.status)
        save = Gtk.Button(label="Kaydet ve uygula")
        save.add_css_class("suggested-action")
        save.connect("clicked", self._save_settings)
        footer.append(save)
        root.append(footer)

    def _add_section(self, parent: Gtk.Box, title: str) -> None:
        heading = Gtk.Label(label=title, xalign=0)
        heading.add_css_class("title-3")
        parent.append(heading)

    def _add_control_row(self, parent: Gtk.Box, label: str, control: Gtk.Widget) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.append(Gtk.Label(label=label, xalign=0))
        control.set_hexpand(True)
        row.append(control)
        parent.append(row)

    def _add_switch(self, parent: Gtk.Box, label: str, key: str) -> None:
        switch = Gtk.Switch()
        switch.set_active(self.config.values[key])
        self._switches[key] = switch
        self._add_control_row(parent, label, switch)

    def _add_spin(
        self, parent: Gtk.Box, label: str, key: str, minimum: int, maximum: int, step: int
    ) -> None:
        spin = Gtk.SpinButton.new_with_range(minimum, maximum, step)
        spin.set_value(self.config.values[key])
        self._spins[key] = spin
        self._add_control_row(parent, label, spin)

    def _available_themes(self) -> list[str]:
        data_home = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
        installed = data_home / "xlauncher" / "themes"
        bundled = Path(__file__).resolve().parent / "themes"
        names = {"default-dark"}
        for directory in (installed, bundled):
            try:
                names.update(
                    child.name
                    for child in directory.iterdir()
                    if child.is_dir() and (child / "theme.css").is_file()
                )
            except OSError:
                continue
        return sorted(names)

    def _selected_theme(self) -> str:
        model = self.theme_dropdown.get_model()
        item = model.get_item(self.theme_dropdown.get_selected())
        return item.get_string() if item is not None else "default-dark"

    def _update_theme_preview(self, *args: object) -> None:
        _ = args
        data_home = Path(
            os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
        theme_name = self._selected_theme()
        candidates = [
            data_home / "xlauncher" / "themes" / theme_name / "theme.css",
            Path(__file__).resolve().parent / "themes" / theme_name / "theme.css",
        ]
        css = DEFAULT_THEME_CSS
        for candidate in candidates:
            try:
                css = candidate.read_text(encoding="utf-8")
                break
            except OSError:
                continue
        self.theme_preview.get_buffer().set_text(css)

    def _refresh_alias_list(self) -> None:
        self._clear_list(self.alias_list)
        self.aliases = load_aliases()
        for alias in self.aliases.values():
            row = Gtk.ListBoxRow()
            row.set_child(
                Gtk.Label(
                    label=f"{alias.key}  →  {alias.value} ({alias.kind})",
                    xalign=0,
                )
            )
            self.alias_list.append(row)

    def _confirm_destructive(
        self,
        title: str,
        message: str,
        confirm_label: str,
        action: Callable[[], None],
    ) -> None:
        if self._confirmation_dialog is not None:
            self._confirmation_dialog.present()
            return
        dialog = Gtk.Window(title=title, transient_for=self, modal=True)
        dialog.set_default_size(360, 140)
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(16)
        content.set_margin_bottom(16)
        content.set_margin_start(16)
        content.set_margin_end(16)
        content.append(Gtk.Label(label=message, xalign=0, wrap=True))
        buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cancel = Gtk.Button(label="Vazgeç")
        confirm = Gtk.Button(label=confirm_label)

        def finish(button: Gtk.Button, accepted: bool) -> None:
            _ = button
            self._confirmation_dialog = None
            dialog.close()
            if accepted:
                action()

        cancel.connect("clicked", finish, False)
        confirm.connect("clicked", finish, True)
        buttons.append(cancel)
        buttons.append(confirm)
        content.append(buttons)
        dialog.set_child(content)
        dialog.connect("close-request", self._on_confirmation_close_request)
        self._confirmation_dialog = dialog
        dialog.present()

    def _on_close_request(self, window: Gtk.Window) -> bool:
        _ = window
        self._confirmation_dialog = None
        return False

    def _on_confirmation_close_request(self, window: Gtk.Window) -> bool:
        if self._confirmation_dialog is window:
            self._confirmation_dialog = None
        return False

    def _save_alias(self, _button: Gtk.Button) -> None:
        _ = _button
        key = self.alias_key.get_text().strip()
        value = self.alias_value.get_text().strip()
        if not key or any(character.isspace() for character in key):
            self.status.set_text("Takma ad boş olamaz veya boşluk içeremez.")
            return
        if self.alias_type.get_selected() == 0:
            if value not in self.app_ids:
                self.status.set_text("Uygulama desktop ID'si kurulu uygulamalarda bulunamadı.")
                return
            alias = Alias(key, "app", value)
        else:
            try:
                validate_web_uri(value)
            except ValueError as error:
                self.status.set_text(str(error))
                return
            alias = Alias(key, "web", value)
        updated = self.aliases.copy()
        updated[key.casefold()] = alias
        if not save_aliases(updated):
            self.status.set_text("Takma ad kaydedilemedi.")
            return
        self._refresh_alias_list()
        self.status.set_text("Takma ad kaydedildi.")

    def _remove_alias(self, _button: Gtk.Button) -> None:
        _ = _button
        row = self.alias_list.get_selected_row()
        if row is None:
            self.status.set_text("Silmek için bir takma ad seçin.")
            return
        alias = list(self.aliases.values())[row.get_index()]

        def remove() -> None:
            updated = self.aliases.copy()
            updated.pop(alias.key.casefold(), None)
            if save_aliases(updated):
                self._refresh_alias_list()
                self.status.set_text("Takma ad silindi.")
            else:
                self.status.set_text("Takma ad silinemedi.")

        self._confirm_destructive(
            "Takma ad silinsin mi?",
            f"{alias.key} takma adı kalıcı olarak silinecek.",
            "Sil",
            remove,
        )

    def _refresh_user_data_lists(self) -> None:
        self._clear_list(self.history_list)
        for entry in load_history():
            app = next(
                (item for item in self.applications if item.desktop_id == entry.desktop_id),
                None,
            )
            label = f"{app.name if app else entry.desktop_id} · {entry.use_count} kez"
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=label, xalign=0))
            self.history_list.append(row)

        self._clear_list(self.favorite_list)
        self.favorite_ids = self.favorites.load(self.app_ids)
        for desktop_id in self.favorite_ids:
            app = next((item for item in self.applications if item.desktop_id == desktop_id), None)
            row = Gtk.ListBoxRow()
            row.set_child(
                Gtk.Label(
                    label=f"★ {app.name if app else desktop_id}",
                    xalign=0,
                )
            )
            self.favorite_list.append(row)

    @staticmethod
    def _clear_list(list_box: Gtk.ListBox) -> None:
        child = list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            list_box.remove(child)
            child = next_child

    def _clear_app_history(self, _button: Gtk.Button) -> None:
        _ = _button
        self._confirm_destructive(
            "Uygulama geçmişini temizle?",
            "Son kullanılan uygulamaların geçmişi kalıcı olarak silinecek.",
            "Temizle",
            self._clear_app_history_now,
        )

    def _clear_app_history_now(self) -> None:
        from history_manager import clear_history

        if clear_history():
            self._refresh_user_data_lists()
            self.status.set_text("Uygulama geçmişi temizlendi.")
        else:
            self.status.set_text("Uygulama geçmişi temizlenemedi.")

    def _remove_favorite(self, _button: Gtk.Button) -> None:
        _ = _button
        row = self.favorite_list.get_selected_row()
        if row is None:
            self.status.set_text("Silmek için bir favori seçin.")
            return
        desktop_id = self.favorite_ids[row.get_index()]

        def remove() -> None:
            remaining = [item for item in self.favorite_ids if item != desktop_id]
            if self.favorites.save(remaining):
                self._refresh_user_data_lists()
                self.status.set_text("Favori kaldırıldı.")
            else:
                self.status.set_text("Favori kaldırılamadı.")

        self._confirm_destructive(
            "Favori kaldırılsın mı?",
            "Seçilen uygulama favorilerden kaldırılacak.",
            "Kaldır",
            remove,
        )

    def _confirm_clear_clipboard(self, _button: Gtk.Button) -> None:
        _ = _button
        self._confirm_destructive(
            "Pano geçmişini temizle?",
            "X-Launcher içinden kopyalanmış metinler kalıcı olarak silinecek.",
            "Temizle",
            self._clear_clipboard_history,
        )

    def _clear_clipboard_history(self) -> None:
        from clipboard_history import clear_clipboard_history

        if clear_clipboard_history():
            self.status.set_text("Pano geçmişi temizlendi.")
        else:
            self.status.set_text("Pano geçmişi temizlenemedi.")

    def _save_settings(self, _button: Gtk.Button) -> None:
        _ = _button
        engine = ["google", "duckduckgo", "brave"][
            min(2, self.engine_dropdown.get_selected())
        ]
        updates = {
            key: control.get_active() for key, control in self._switches.items()
        }
        updates.update(
            {key: int(control.get_value()) for key, control in self._spins.items()}
        )
        updates.update(
            {
                "search_engine": engine,
                "active_theme": self._selected_theme(),
            }
        )
        if not self.config.save(updates):
            self.status.set_text("Ayarlar kaydedilemedi.")
            return
        self.on_saved()
        self.status.set_text("Ayarlar kaydedildi.")
