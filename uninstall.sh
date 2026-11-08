#!/bin/sh
set -eu

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

for file in \
    main.py calculator.py web_search.py desktop_parser.py fuzzy_search.py \
    app_launcher.py app_launch_context.py toggle_daemon.py history_manager.py alias_manager.py \
    theme_manager.py config_manager.py favorites_manager.py providers.py \
    command_router.py clipboard_history.py preferences_window.py version.py \
    launcher_cli.py doctor.py appimage_integration.py help_content.py \
    xlauncher-toggle
do
    rm -f "$APP_DIR/$file"
done
rm -f "$APP_DIR/themes/default-dark/theme.css"
for directory in "$APP_DIR/themes/default-dark" "$APP_DIR/themes" "$APP_DIR"; do
    if [ -d "$directory" ] && ! rmdir "$directory" 2>/dev/null; then
        printf 'Kullanıcı verisi korundu: %s\n' "$directory"
    fi
done
rm -f "$BIN_DIR/xlauncher" "$BIN_DIR/xlauncher-uninstall"
rm -f "$APPLICATIONS_DIR/xlauncher.desktop"
rm -f "$ICONS_DIR/xlauncher.svg"

if command -v update-desktop-database >/dev/null 2>&1 && [ -d "$APPLICATIONS_DIR" ]; then
    update-desktop-database "$APPLICATIONS_DIR"
fi

printf 'X-Launcher kaldırıldı. Kullanıcı ayarları ve verileri %s/xlauncher altında korundu.\n' "$DATA_HOME"
