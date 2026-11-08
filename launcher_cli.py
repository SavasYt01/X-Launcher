"""Handle GUI-independent commands before importing GTK."""

import argparse
import os
import sys

from version import APP_NAME, VERSION


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xlauncher",
        description="GTK4 Linux uygulama başlatıcısı",
        epilog=(
            "Komutlar: --toggle, --stop, --reload, --reload-apps, --doctor, "
            "--integrate, --unintegrate"
        ),
    )
    commands = parser.add_mutually_exclusive_group()
    commands.add_argument("--version", action="store_true", help="sürümü göster")
    commands.add_argument("--doctor", action="store_true", help="çevrimdışı sistem tanılaması")
    commands.add_argument("--integrate", action="store_true", help="AppImage'ı kullanıcı menüsüne ekle")
    commands.add_argument("--unintegrate", action="store_true", help="AppImage menü girdisini kaldır")
    return parser


def dispatch(
    arguments: list[str] | None = None,
) -> int | None:
    """Run a standalone command, or return None for the GTK application."""
    args = list(sys.argv[1:] if arguments is None else arguments)
    if len(args) != 1 or args[0] not in {
        "--help",
        "-h",
        "--version",
        "--doctor",
        "--integrate",
        "--unintegrate",
    }:
        return None

    if args[0] in {"--help", "-h"}:
        _parser().print_help()
        return 0
    if args[0] == "--version":
        print(f"{APP_NAME} {VERSION}")
        return 0
    if args[0] == "--doctor":
        from doctor import run

        return run()

    if not os.environ.get("APPIMAGE"):
        print(
            "Bu masaüstü entegrasyonu yalnızca AppImage içinden kullanılabilir. "
            "Yerel kurulum dosyalarınız değiştirilmedi.",
            file=sys.stderr,
        )
        return 1
    from appimage_integration import integrate, unintegrate

    return integrate() if args[0] == "--integrate" else unintegrate()
