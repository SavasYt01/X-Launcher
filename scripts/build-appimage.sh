#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PYTHON=${PYTHON:-/usr/bin/python3}
APPIMAGETOOL_SHA256=b90f4a8b18967545fda78a445b27680a1642f1ef9488ced28b65398f2be7add2
APPIMAGETOOL_URL=https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
TOOL_CACHE=${XDG_CACHE_HOME:-"${HOME:?HOME must be set}/.cache"}/xlauncher/tools
TOOL=${APPIMAGETOOL:-$TOOL_CACHE/appimagetool-x86_64.AppImage}
DIST_DIR=${XLAUNCHER_DIST_DIR:-$PROJECT_DIR/dist}
BUILD_WORK=$(mktemp -d "${TMPDIR:-/tmp}/xlauncher-appimage.XXXXXX")
trap 'rm -rf -- "$BUILD_WORK"' EXIT

if [[ $(uname -m) != x86_64 ]]; then
    printf 'AppImage derlemesi yalnızca x86_64 üzerinde desteklenir.\n' >&2
    exit 1
fi
if [[ ! -x "$PYTHON" ]] || ! "$PYTHON" -c 'import gi; gi.require_version("Gtk", "4.0"); from gi.repository import Gtk' >/dev/null 2>&1; then
    printf 'GTK4 PyGObject içeren sistem Python bulunamadı: %s\n' "$PYTHON" >&2
    exit 1
fi

if [[ ! -f "$TOOL" ]]; then
    if [[ -n "${APPIMAGETOOL:-}" ]]; then
        printf 'Belirtilen appimagetool dosyası bulunamadı: %s\n' "$TOOL" >&2
        exit 1
    fi
    mkdir -p "$TOOL_CACHE"
    curl --fail --location --retry 3 "$APPIMAGETOOL_URL" --output "$BUILD_WORK/appimagetool"
    printf '%s  %s\n' "$APPIMAGETOOL_SHA256" "$BUILD_WORK/appimagetool" | sha256sum --check
    install -m 0755 "$BUILD_WORK/appimagetool" "$TOOL"
fi
printf '%s  %s\n' "$APPIMAGETOOL_SHA256" "$TOOL" | sha256sum --check

APPDIR=$BUILD_WORK/AppDir
"$PYTHON" "$PROJECT_DIR/scripts/build_appdir.py" "$APPDIR"

mkdir -p "$DIST_DIR"
VERSION=$("$PYTHON" -c 'import sys; sys.path.insert(0, sys.argv[1]); from version import VERSION; print(VERSION)' "$PROJECT_DIR")
ARTIFACT=$DIST_DIR/X-Launcher-$VERSION-x86_64.AppImage
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$TOOL" "$APPDIR" "$ARTIFACT"
chmod 0755 "$ARTIFACT"
(cd "$DIST_DIR" && sha256sum "$(basename "$ARTIFACT")" > SHA256SUMS)

bash "$PROJECT_DIR/scripts/test-appimage.sh" "$ARTIFACT"
printf 'AppImage ve SHA256SUMS hazır: %s\n' "$DIST_DIR"
