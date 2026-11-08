#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ $# -gt 1 ]]; then
    printf 'Kullanım: %s [AppImage]\n' "$0" >&2
    exit 2
fi
if [[ $# -eq 1 ]]; then
    ARTIFACT=$(realpath -- "$1")
else
    VERSION=$(/usr/bin/python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from version import VERSION; print(VERSION)' "$PROJECT_DIR")
    ARTIFACT=$PROJECT_DIR/dist/X-Launcher-$VERSION-x86_64.AppImage
fi

if [[ ! -f "$ARTIFACT" || ! -x "$ARTIFACT" ]]; then
    printf 'AppImage bulunamadı veya çalıştırılabilir değil: %s\n' "$ARTIFACT" >&2
    exit 1
fi

/usr/bin/python3 - "$ARTIFACT" <<'PY'
import struct
import sys
from pathlib import Path

artifact = Path(sys.argv[1])
with artifact.open("rb") as image:
    header = image.read(20)
if len(header) < 20 or header[:4] != b"\x7fELF" or header[8:11] != b"AI\x02":
    raise SystemExit("Dosya geçerli bir AppImage Type 2 değil.")
if header[4] != 2 or struct.unpack("<H", header[18:20])[0] != 62:
    raise SystemExit("AppImage x86_64 ELF hedefi değil.")
PY

ARTIFACT_DIR=$(dirname -- "$ARTIFACT")
if [[ -f "$ARTIFACT_DIR/SHA256SUMS" ]]; then
    (cd "$ARTIFACT_DIR" && sha256sum --check SHA256SUMS)
fi

EXPECTED_VERSION=$(/usr/bin/python3 -c 'import sys; sys.path.insert(0, sys.argv[1]); from version import VERSION; print(VERSION)' "$PROJECT_DIR")
APPIMAGE_EXTRACT_AND_RUN=1 "$ARTIFACT" --version | grep --fixed-strings --line-regexp "X-Launcher $EXPECTED_VERSION"

TEST_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/xlauncher appimage test.XXXXXX")
trap 'rm -rf -- "$TEST_ROOT"' EXIT
(
    cd "$TEST_ROOT"
    APPIMAGE_EXTRACT_AND_RUN=1 "$ARTIFACT" --appimage-extract
)
APPDIR=$TEST_ROOT/squashfs-root
if [[ ! -x "$APPDIR/AppRun" || ! -f "$APPDIR/xlauncher.desktop" || ! -f "$APPDIR/xlauncher.svg" || ! -f "$APPDIR/.DirIcon" ]]; then
    printf 'AppDir kök dosyaları eksik.\n' >&2
    exit 1
fi
desktop_count=$(find "$APPDIR" -maxdepth 1 -type f -name '*.desktop' -printf '.' | wc -c)
if [[ "$desktop_count" -ne 1 ]] || ! grep --quiet --fixed-strings 'Icon=xlauncher' "$APPDIR/xlauncher.desktop"; then
    printf 'AppDir kökünde tek, eşleşen masaüstü girdisi bulunmalı.\n' >&2
    exit 1
fi
/usr/bin/python3 - "$APPDIR/.DirIcon" <<'PY'
import sys
from pathlib import Path

if not Path(sys.argv[1]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
    raise SystemExit("AppDir .DirIcon geçerli PNG değil.")
PY
(
    export APPDIR
    export APPIMAGE="$ARTIFACT"
    export XDG_CACHE_HOME="$TEST_ROOT/cache"
    . "$APPDIR/usr/share/xlauncher/appimage-env.sh"
    xlauncher_prepare_environment
    xlauncher_prepare_pixbuf_cache
    test -f "$GDK_PIXBUF_MODULE_FILE"
    grep --quiet --fixed-strings "$APPDIR" "$GDK_PIXBUF_MODULE_FILE"
    "$APPDIR/usr/bin/python3" -c \
        'import gi,sys; gi.require_version("GdkPixbuf","2.0"); from gi.repository import GdkPixbuf; image=GdkPixbuf.Pixbuf.new_from_file(sys.argv[1]); assert image.get_width() > 0' \
        "$APPDIR/xlauncher.svg"
)
if command -v desktop-file-validate >/dev/null 2>&1; then
    desktop-file-validate "$APPDIR/xlauncher.desktop"
fi

APPIMAGE="$ARTIFACT" "$APPDIR/AppRun" --version
APPIMAGE="$ARTIFACT" "$APPDIR/AppRun" --help >/dev/null
APPIMAGE="$ARTIFACT" "$APPDIR/AppRun" --doctor

TEST_HOME=$TEST_ROOT/home
XDG_DATA_HOME=$TEST_HOME/.local/share
mkdir -p "$XDG_DATA_HOME/applications"
printf 'native desktop entry\n' > "$XDG_DATA_HOME/applications/xlauncher.desktop"
export APPIMAGE="$ARTIFACT"
export HOME="$TEST_HOME"
export XDG_DATA_HOME
APPIMAGE="$ARTIFACT" "$APPDIR/AppRun" --integrate
test -f "$XDG_DATA_HOME/applications/xlauncher-appimage.desktop"
test -f "$XDG_DATA_HOME/icons/hicolor/scalable/apps/xlauncher-appimage.svg"
grep --quiet --fixed-strings --line-regexp 'native desktop entry' \
    "$XDG_DATA_HOME/applications/xlauncher.desktop"
APPIMAGE="$ARTIFACT" "$APPDIR/AppRun" --unintegrate
test ! -e "$XDG_DATA_HOME/applications/xlauncher-appimage.desktop"
test ! -e "$XDG_DATA_HOME/icons/hicolor/scalable/apps/xlauncher-appimage.svg"
grep --quiet --fixed-strings --line-regexp 'native desktop entry' \
    "$XDG_DATA_HOME/applications/xlauncher.desktop"

printf 'AppImage smoke test geçti: %s\n' "$ARTIFACT"
