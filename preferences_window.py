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
        self.set_default_size(740, 800)
        self.set_resizable(True)
        self.connect("close-request", self._on_close_request)
        self.config = config
        self.applications = applications
        self.on_saved = on_saved
        self._confirmation_dialog: Gtk.Window | None = None
        self._preview_provider: Gtk.CssProvider | None = None
        display = self.get_display()
        if display is not None:
            self._preview_provider = Gtk.CssProvider()
            Gtk.StyleContext.add_provider_for_display(
                display,
                self._preview_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
            )
        self.favorites = FavoritesManager()
        self.aliases = load_aliases()
        self.app_ids = {application.desktop_id for application in applications}
        self._switches: dict[str, Gtk.Switch] = {}
        self._spins: dict[str, Gtk.SpinButton] = {}
        self.status = Gtk.Label(xalign=0)
        self.status.set_hexpand(True)
        self.status.set_wrap(True)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(18)
        root.set_margin_bottom(12)
        root.set_margin_start(18)
        root.set_margin_end(18)
        self.set_child(root)

        heading = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title = Gtk.Label(label="Ayarlar", xalign=0)
        title.add_css_class("title-1")
        heading.append(title)
        heading.append(
            Gtk.Label(
                label="Arama, görünüm ve yerel verilerinizi yönetin.",
                xalign=0,
            )
        )
        root.append(heading)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        scroller.set_child(body)
        root.append(scroller)

        general = self._add_section(
            body, "Genel", "Başlatıcının temel davranışları."
        )
        self._add_spin(
            general,
            "Otomatik tarama aralığı (saniye, 0 = kapalı)",
            "refresh_interval_seconds",
            0,
            3600,
            10,
        )

        search = self._add_section(
            body, "Arama", "Arama motoru ve sonuç sıralaması."
        )
        self._add_spin(search, "Sonuç sayısı", "result_limit", 3, 20, 1)
        self._add_spin(search, "Geçmiş sıralama katkısı", "history_boost", 0, 100, 5)
        self.engine_dropdown = Gtk.DropDown.new_from_strings(
            ["Google", "DuckDuckGo", "Brave Search"]
        )
        self.engine_dropdown.set_selected(
            {"google": 0, "duckduckgo": 1, "brave": 2}.get(
                config.values["search_engine"], 0
            )
        )
        self._add_control_row(search, "Varsayılan arama motoru", self.engine_dropdown)

        appearance = self._add_section(
            body, "Görünüm", "Tema seçimini kaydetmeden önce önizleyin."
        )
        theme_names = self._available_themes()
        self.theme_dropdown = Gtk.DropDown.new_from_strings(theme_names)
        current_theme = config.values["active_theme"]
        self.theme_dropdown.set_selected(
            theme_names.index(current_theme) if current_theme in theme_names else 0
        )
        self.theme_dropdown.connect("notify::selected", self._update_theme_preview)
        self._add_control_row(appearance, "Aktif tema", self.theme_dropdown)
        self.theme_preview = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=8,
        )
        self.theme_preview.add_css_class("launcher-surface")
        self.theme_preview.set_margin_top(4)
        self.theme_preview.set_margin_bottom(4)
        preview_entry = Gtk.Entry()
        preview_entry.add_css_class("launcher-entry")
        preview_entry.set_placeholder_text("Uygulama ara")
        self.theme_preview.append(preview_entry)
        preview_list = Gtk.ListBox()
        preview_list.add_css_class("launcher-results")
        preview_row = Gtk.ListBoxRow()
        preview_row.add_css_class("launcher-results")
        preview_row.set_child(
            Gtk.Label(label="Örnek sonuç  ·  Önizleme", xalign=0)
        )
        preview_list.append(preview_row)
        preview_list.select_row(preview_row)
        self.theme_preview.append(preview_list)
        appearance.append(self.theme_preview)
        self._update_theme_preview()

        aliases_section = self._add_section(
            body, "Takma adlar", "Kısa bir anahtarı uygulamaya veya web adresine bağlayın."
        )
        self.alias_list = Gtk.ListBox()
        self.alias_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.alias_list.add_css_class("boxed-list")
        self.alias_list.connect("row-selected", self._on_alias_selected)
        alias_scroll = Gtk.ScrolledWindow()
        alias_scroll.set_min_content_height(100)
        alias_scroll.set_max_content_height(180)
        alias_scroll.set_child(self.alias_list)
        aliases_section.append(alias_scroll)
        self.alias_key = Gtk.Entry()
        self.alias_key.set_placeholder_text("Takma ad (örn. yt)")
        self.alias_value = Gtk.Entry()
        self.alias_value.set_placeholder_text("Desktop ID veya https:// adresi")
        self.alias_type = Gtk.DropDown.new_from_strings(["Uygulama", "Web adresi"])
        self._add_control_row(aliases_section, "Tür", self.alias_type)
        self._add_control_row(aliases_section, "Takma ad", self.alias_key)
        self._add_control_row(aliases_section, "Hedef", self.alias_value)
        aliases_section.append(
            Gtk.Label(
                label=(
                    "Uygulama için kurulu desktop ID kullanın; web adresi "
                    "http:// veya https:// ile başlamalıdır. Seçili takma ad "
                    "alanlara yüklenir ve buradan güncellenebilir."
                ),
                xalign=0,
                wrap=True,
            )
        )
        alias_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        add_alias = Gtk.Button(label="Ekle / Güncelle")
        add_alias.connect("clicked", self._save_alias)
        new_alias = Gtk.Button(label="Yeni")
        new_alias.connect("clicked", self._clear_alias_form)
        remove_alias = Gtk.Button(label="Seçileni sil")
        remove_alias.connect("clicked", self._remove_alias)
        alias_buttons.append(add_alias)
        alias_buttons.append(new_alias)
        alias_buttons.append(remove_alias)
        aliases_section.append(alias_buttons)
        self._refresh_alias_list()

        history_section = self._add_section(
            body, "Geçmiş ve favoriler", "Bu veriler yalnızca bu kullanıcı hesabında saklanır."
        )
        self._add_switch(
            history_section,
            "Son kullanılanları boş aramada göster",
            "show_recent_on_empty",
        )
        self._add_switch(
            history_section,
            "Favorileri boş aramada göster",
            "show_favorites_on_empty",
        )
        self._add_switch(history_section, "Geçmişe göre sonuçları öne çıkar", "show_recent")
        self._add_switch(history_section, "Favorileri aramada öne çıkar", "show_favorites")
        self._add_spin(history_section, "Maksimum uygulama geçmişi", "max_history", 1, 200, 1)
        self.history_list = Gtk.ListBox()
        self.history_list.set_selection_mode(Gtk.SelectionMode.NONE)
        history_section.append(self.history_list)
        clear_history = Gtk.Button(label="Uygulama geçmişini temizle")
        clear_history.connect("clicked", self._clear_app_history)
        history_section.append(clear_history)
        self.favorite_list = Gtk.ListBox()
        history_section.append(self.favorite_list)
        remove_favorite = Gtk.Button(label="Seçili favoriyi sil")
        remove_favorite.connect("clicked", self._remove_favorite)
        history_section.append(remove_favorite)
        self._refresh_user_data_lists()

        clipboard_section = self._add_section(
            body, "Pano", "Yalnızca X-Launcher içindeki açık kopyalama işlemleri kaydedilir."
        )
        self._add_switch(
            clipboard_section,
            "X-Launcher kopyalama geçmişini etkinleştir",
            "clipboard_history_enabled",
        )
        self._add_spin(
            clipboard_section,
            "Maksimum pano kaydı",
            "max_clipboard_history",
            1,
            200,
            1,
        )
        clear_clipboard = Gtk.Button(label="Pano geçmişini temizle")
        clear_clipboard.connect("clicked", self._confirm_clear_clipboard)
        clipboard_section.append(clear_clipboard)
        privacy = Gtk.Label(
            label="Sistem panosu arka planda izlenmez.",
            xalign=0,
            wrap=True,
        )
        clipboard_section.append(privacy)

        root.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        footer.set_halign(Gtk.Align.END)
        footer.append(self.status)
        save = Gtk.Button(label="Kaydet ve uygula")
        save.add_css_class("suggested-action")
        save.set_can_default(True)
        save.connect("clicked", self._save_settings)
        footer.append(save)
        root.append(footer)

    def _add_section(
        self,
        parent: Gtk.Box,
        title: str,
        description: str,
    ) -> Gtk.Box:
        frame = Gtk.Frame(label=title)
        frame.add_css_class("card")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(14)
        content.set_margin_end(14)
        if description:
            note = Gtk.Label(label=description, xalign=0, wrap=True)
            note.add_css_class("dim-label")
            content.append(note)
        frame.set_child(content)
        parent.append(frame)
        return content

    def _add_control_row(self, parent: Gtk.Box, label: str, control: Gtk.Widget) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.add_css_class("preferences-row")
        row.set_valign(Gtk.Align.CENTER)
        label_widget = Gtk.Label(label=label, xalign=0, wrap=True)
        label_widget.set_hexpand(True)
        row.append(label_widget)
        control.set_hexpand(isinstance(control, (Gtk.DropDown, Gtk.Entry)))
        control.set_halign(Gtk.Align.FILL if control.get_hexpand() else Gtk.Align.END)
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
        loaded = False
        for candidate in candidates:
            try:
                css = candidate.read_text(encoding="utf-8")
                loaded = True
                break
            except (OSError, UnicodeError):
                continue
        if not loaded:
            self.status.set_text("Tema önizlenemedi; varsayılan tema gösteriliyor.")
        provider = Gtk.CssProvider()
        errors: list[str] = []

        def parsing_error(
            css_provider: Gtk.CssProvider,
            section: Gtk.CssSection,
            error: Exception,
        ) -> None:
            _ = css_provider, section
            errors.append(str(error))

        provider.connect("parsing-error", parsing_error)
        provider.load_from_string(css)
        if errors:
            fallback = Gtk.CssProvider()
            fallback.load_from_string(DEFAULT_THEME_CSS)
            self.status.set_text(
                "Tema CSS'si geçersiz; varsayılan tema önizleniyor."
            )
            provider = fallback
        elif loaded:
            self.status.set_text("")
        if self._preview_provider is not None:
            display = self.get_display()
            if display is not None:
                Gtk.StyleContext.remove_provider_for_display(
                    display,
                    self._preview_provider,
                )
                self._preview_provider = provider
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1,
                )

    def _refresh_alias_list(self) -> None:
        self._clear_list(self.alias_list)
        self.aliases = load_aliases()
        for alias in self.aliases.values():
            row = Gtk.ListBoxRow()
            row.add_css_class("preferences-alias-row")
            row.set_child(
                Gtk.Label(
                    label=f"{alias.key}  →  {alias.value} ({alias.kind})",
                    xalign=0,
                )
            )
            self.alias_list.append(row)

    def _on_alias_selected(
        self,
        list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if list_box is not self.alias_list or row is None:
            return
        aliases = list(self.aliases.values())
        index = row.get_index()
        if not 0 <= index < len(aliases):
            return
        alias = aliases[index]
        self.alias_key.set_text(alias.key)
        self.alias_value.set_text(alias.value)
        self.alias_type.set_selected(0 if alias.kind == "app" else 1)

    def _clear_alias_form(self, _button: Gtk.Button) -> None:
        _ = _button
        self.alias_list.unselect_all()
        self.alias_key.set_text("")
        self.alias_value.set_text("")
        self.alias_type.set_selected(0)
        self.status.set_text("Yeni takma ad için tür, ad ve hedefi girin.")

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
        display = self.get_display()
        if display is not None and self._preview_provider is not None:
            Gtk.StyleContext.remove_provider_for_display(
                display,
                self._preview_provider,
            )
            self._preview_provider = None
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
