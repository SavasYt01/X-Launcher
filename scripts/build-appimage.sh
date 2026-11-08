#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
BUILDER=${APPIMAGE_BUILDER:-appimage-builder}

if ! command -v "$BUILDER" >/dev/null 2>&1 && [[ ! -x "$BUILDER" ]]; then
    printf 'appimage-builder was not found. Set APPIMAGE_BUILDER to its executable path.\n' >&2
    exit 1
fi

cd "$PROJECT_DIR"
exec "$BUILDER" --recipe packaging/AppImageBuilder.yml --skip-test
