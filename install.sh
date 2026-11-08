#!/bin/sh
set -eu

PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON=${XLAUNCHER_PYTHON:-/usr/bin/python3}
DATA_HOME=${XDG_DATA_HOME:-"${HOME:?HOME must be set}/.local/share"}
BIN_DIR=${XLAUNCHER_BIN_DIR:-"${HOME:?HOME must be set}/.local/bin"}
APPLICATIONS_DIR=${XDG_DATA_HOME:-"${HOME:?HOME must be set}/.local/share"}/applications
ICONS_DIR=${XDG_DATA_HOME:-"${HOME:?HOME must be set}/.local/share"}/icons/hicolor/scalable/apps
APP_DIR=$DATA_HOME/xlauncher

case "$DATA_HOME:$BIN_DIR:$APPLICATIONS_DIR:$ICONS_DIR" in
    /*:/*:/*:/*) ;;
    *)
        printf 'XDG data and bin directories must be absolute paths.\n' >&2
        exit 1
        ;;
esac

if [ ! -x "$PYTHON" ]; then
    printf 'Python interpreter not found or not executable: %s\n' "$PYTHON" >&2
    exit 1
fi

if ! "$PYTHON" -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    printf 'GTK4 PyGObject is unavailable for %s.\n' "$PYTHON" >&2
    printf 'On Ubuntu, install it with: sudo apt install python3-gi gir1.2-gtk-4.0\n' >&2
    exit 1
fi

mkdir -p "$APP_DIR" "$APP_DIR/themes/default-dark" "$BIN_DIR" "$APPLICATIONS_DIR" "$ICONS_DIR"
for file in main.py calculator.py web_search.py desktop_parser.py fuzzy_search.py app_launcher.py toggle_daemon.py history_manager.py alias_manager.py theme_manager.py config_manager.py favorites_manager.py providers.py command_router.py clipboard_history.py preferences_window.py version.py; do
    install -m 0644 "$PROJECT_DIR/$file" "$APP_DIR/$file"
done
install -m 0644 "$PROJECT_DIR/themes/default-dark/theme.css" "$APP_DIR/themes/default-dark/theme.css"
install -m 0755 "$PROJECT_DIR/xlauncher-toggle" "$APP_DIR/xlauncher-toggle"
install -m 0755 "$PROJECT_DIR/uninstall.sh" "$BIN_DIR/xlauncher-uninstall"
install -m 0644 "$PROJECT_DIR/packaging/xlauncher.svg" "$ICONS_DIR/xlauncher.svg"

{
    printf '#!/bin/sh\nexec '
    "$PYTHON" -c 'import shlex,sys; print(shlex.quote(sys.argv[1]), shlex.quote(sys.argv[2]), "\"$@\"", sep=" ")' \
        "$PYTHON" "$APP_DIR/xlauncher-toggle"
} > "$BIN_DIR/xlauncher"
chmod 0755 "$BIN_DIR/xlauncher"

"$PYTHON" - "$BIN_DIR/xlauncher" "$APPLICATIONS_DIR/xlauncher.desktop" <<'PY'
import sys
from pathlib import Path


def desktop_quote(value: str) -> str:
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    value = value.replace("`", "\\`").replace("$", "\\$")
    value = value.replace("%", "%%")
    return f'"{value}"'


executable = desktop_quote(str(Path(sys.argv[1])))
desktop_file = Path(sys.argv[2])
desktop_file.write_text(
    "[Desktop Entry]\n"
    "Name=X-Launcher\n"
    "Comment=Hizli ve modern uygulama baslatici\n"
    f"Exec={executable}\n"
    "Icon=xlauncher\n"
    "Type=Application\n"
    "Categories=Utility;\n"
    "Terminal=false\n"
    "StartupNotify=false\n",
    encoding="utf-8",
)
PY

if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$APPLICATIONS_DIR"
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f -t "${XDG_DATA_HOME:-"$HOME/.local/share"}/icons/hicolor" || \
        printf 'Warning: GTK icon cache could not be refreshed.\n' >&2
fi

printf 'X-Launcher installed for this user.\n'
printf 'Launcher: %s/xlauncher\n' "$BIN_DIR"
printf 'Shortcut command: %s/xlauncher\n' "$BIN_DIR"
printf 'Desktop entry: %s/xlauncher.desktop\n' "$APPLICATIONS_DIR"
