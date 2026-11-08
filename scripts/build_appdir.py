#!/usr/bin/env python3
"""Assemble a relocatable GTK4/PyGObject AppDir from an Ubuntu build host."""

from __future__ import annotations

import ctypes.util
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPDIR_MODULES = (
    "main.py",
    "calculator.py",
    "web_search.py",
    "desktop_parser.py",
    "fuzzy_search.py",
    "app_launcher.py",
    "app_launch_context.py",
    "toggle_daemon.py",
    "history_manager.py",
    "alias_manager.py",
    "theme_manager.py",
    "config_manager.py",
    "favorites_manager.py",
    "providers.py",
    "command_router.py",
    "clipboard_history.py",
    "preferences_window.py",
    "version.py",
    "launcher_cli.py",
    "doctor.py",
    "appimage_integration.py",
    "help_content.py",
)
REQUIRED_LIBRARIES = ("gtk-4",)
SYSTEM_LIBRARY_ROOT = Path("/usr/lib/x86_64-linux-gnu")
ELF_MAGIC = b"\x7fELF"
_HOST_GLIBC_LIBRARY = re.compile(
    r"(?:libc|libm|libmvec|libpthread|libdl|librt|libresolv|libnss_[^.]+|"
    r"libutil|libanl|libBrokenLocale|libthread_db)\.so(?:\.|$)"
)


def _run(arguments: list[str], *, capture: bool = True) -> str:
    result = subprocess.run(
        arguments,
        check=False,
        capture_output=capture,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"Komut başarısız ({result.returncode}): {' '.join(arguments)}\n"
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip() if capture else ""


def _copy_file(source: Path, destination: Path, *, executable: bool = False) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination, follow_symlinks=True)
    if executable:
        destination.chmod(destination.stat().st_mode | 0o111)


def _copy_tree(source: Path, destination: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(f"Gerekli paket dizini bulunamadı: {source}")
    shutil.copytree(source, destination, symlinks=True, dirs_exist_ok=True)


def _find_gdk_pixbuf_loaders() -> tuple[list[Path], Path]:
    module_dir = Path(
        _run(["pkg-config", "--variable=gdk_pixbuf_moduledir", "gdk-pixbuf-2.0"])
    )
    loaders = sorted(module_dir.glob("*.so"))
    if not loaders:
        raise FileNotFoundError(f"GdkPixbuf yükleyicileri bulunamadı: {module_dir}")
    query = shutil.which("gdk-pixbuf-query-loaders")
    if query is None and not (module_dir.parent / "loaders.cache").is_file():
        raise FileNotFoundError("GdkPixbuf yükleyici önbelleği bulunamadı.")
    return loaders, Path(query) if query else module_dir.parent / "loaders.cache"


def _elf_dependencies(elf_file: Path) -> set[Path]:
    if not elf_file.is_file():
        return set()
    with elf_file.open("rb") as file:
        if file.read(4) != ELF_MAGIC:
            return set()
    result = subprocess.run(
        ["ldd", str(elf_file)],
        check=False,
        capture_output=True,
        text=True,
    )
    output = f"{result.stdout}\n{result.stderr}"
    if result.returncode and "not a dynamic executable" not in output:
        raise RuntimeError(f"Paylaşılan kütüphaneler okunamadı: {elf_file}\n{output}")
    if "not found" in output:
        raise RuntimeError(f"Eksik paylaşılan kütüphane: {elf_file}\n{output}")

    dependencies: set[Path] = set()
    for line in output.splitlines():
        match = re.search(r"=>\s+(/[^ ]+)\s+\(", line)
        if match is None:
            match = re.match(r"\s*(/[^ ]+)\s+\(", line)
        if match is not None:
            dependency = Path(match.group(1))
            if dependency.is_file():
                dependencies.add(dependency)
    return dependencies


def _dependency_closure(roots: list[Path]) -> set[Path]:
    dependencies: set[Path] = set()
    pending = list(roots)
    visited: set[Path] = set()
    while pending:
        current = pending.pop()
        resolved = current.resolve()
        if resolved in visited:
            continue
        visited.add(resolved)
        if ".so" in current.name and not _HOST_GLIBC_LIBRARY.match(current.name):
            dependencies.add(current)
        for dependency in _elf_dependencies(resolved):
            if (
                not _HOST_GLIBC_LIBRARY.match(dependency.name)
                and dependency not in dependencies
            ):
                dependencies.add(dependency)
                pending.append(dependency)
    return dependencies


def _find_required_libraries() -> list[Path]:
    ldconfig_output = _run(["ldconfig", "-p"])
    result = []
    for name in REQUIRED_LIBRARIES:
        library = ctypes.util.find_library(name)
        if library is None:
            raise FileNotFoundError(f"Gerekli sistem kütüphanesi bulunamadı: {name}")
        match = re.search(
            rf"^\s*{re.escape(library)}\s+\([^)]*\)\s+=>\s+(\S+)$",
            ldconfig_output,
            flags=re.MULTILINE,
        )
        if match is None:
            raise FileNotFoundError(f"Kütüphane yolu çözümlenemedi: {library}")
        result.append(Path(match.group(1)))
    return result


def _copy_python_runtime(appdir: Path) -> list[Path]:
    python_binary = Path(sys.executable).resolve()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    python_directory = appdir / "usr" / "lib" / f"python{python_version}"
    _copy_tree(Path(sysconfig.get_paths()["stdlib"]), python_directory)

    binary_destination = appdir / "usr" / "bin" / python_binary.name
    _copy_file(python_binary, binary_destination, executable=True)
    python_link = appdir / "usr" / "bin" / "python3"
    python_link.symlink_to(python_binary.name)

    import gi

    gi_package = Path(gi.__file__).resolve().parent
    gi_destination = appdir / "usr" / "lib" / "python3" / "dist-packages" / "gi"
    _copy_tree(gi_package, gi_destination)

    import_roots = [python_binary]
    import_roots.extend(python_directory.glob("lib-dynload/*.so"))
    import_roots.extend(gi_destination.glob("**/*.so"))
    return import_roots


def _copy_gtk_runtime(appdir: Path) -> list[Path]:
    gtk_modules = SYSTEM_LIBRARY_ROOT / "gtk-4.0"
    gdk_modules = SYSTEM_LIBRARY_ROOT / "gdk-pixbuf-2.0"
    gio_modules = SYSTEM_LIBRARY_ROOT / "gio" / "modules"
    module_roots: list[Path] = []
    for source, relative_destination in (
        (gtk_modules, Path("usr/lib/x86_64-linux-gnu/gtk-4.0")),
        (gdk_modules, Path("usr/lib/x86_64-linux-gnu/gdk-pixbuf-2.0")),
        (gio_modules, Path("usr/lib/x86_64-linux-gnu/gio/modules")),
    ):
        if source.is_dir():
            destination = appdir / relative_destination
            _copy_tree(source, destination)
            module_roots.extend(destination.glob("**/*.so"))
    gio_cache = shutil.which("gio-querymodules")
    gio_module_directory = appdir / "usr" / "lib" / "x86_64-linux-gnu" / "gio" / "modules"
    if gio_module_directory.is_dir():
        if gio_cache is None:
            raise FileNotFoundError("gio-querymodules komutu bulunamadı.")
        _run([gio_cache, str(gio_module_directory)])
    loaders, query = _find_gdk_pixbuf_loaders()
    destination_root = appdir / "usr" / "lib" / "x86_64-linux-gnu"
    copied_loaders = []
    for loader in loaders:
        relative = loader.relative_to(SYSTEM_LIBRARY_ROOT)
        destination = destination_root / relative
        _copy_file(loader, destination)
        copied_loaders.append(destination)
        module_roots.append(loader)

    if query.name == "loaders.cache":
        loader_cache = query.read_text(encoding="utf-8")
        cache_paths = re.findall(r'^"(/[^"\n]+\.so)"$', loader_cache, re.MULTILINE)
        loaders = [Path(path) for path in cache_paths if Path(path).is_file()]
        copied_loaders = []
        for loader in loaders:
            relative = loader.relative_to(Path("/usr"))
            destination = appdir / "usr" / relative
            _copy_file(loader, destination)
            copied_loaders.append(destination)
            module_roots.append(loader)
    else:
        loader_cache = _run([str(query), *(str(loader) for loader in loaders)])
    for source, destination in zip(loaders, copied_loaders, strict=True):
        relative = destination.relative_to(appdir / "usr")
        loader_cache = loader_cache.replace(
            str(source),
            f"@APPDIR@/usr/{relative.as_posix()}",
        )
    cache_path = appdir / "usr" / "share" / "xlauncher" / "gdk-pixbuf-loaders.cache"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(loader_cache + "\n", encoding="utf-8")
    return module_roots


def _copy_typelibs(appdir: Path) -> None:
    sources = (
        Path("/usr/lib/x86_64-linux-gnu/girepository-1.0"),
        Path("/usr/lib/girepository-1.0"),
    )
    destination = appdir / "usr" / "lib" / "x86_64-linux-gnu" / "girepository-1.0"
    found = False
    for source in sources:
        if source.is_dir():
            _copy_tree(source, destination)
            found = True
    if not found:
        raise FileNotFoundError("GObject Introspection typelib dizini bulunamadı.")


def _copy_resources(appdir: Path) -> None:
    for module in APPDIR_MODULES:
        _copy_file(ROOT / module, appdir / "usr" / "bin" / module)
    _copy_file(
        ROOT / "xlauncher-toggle",
        appdir / "usr" / "bin" / "xlauncher-toggle",
        executable=True,
    )
    _copy_file(
        ROOT / "themes" / "default-dark" / "theme.css",
        appdir / "usr" / "bin" / "themes" / "default-dark" / "theme.css",
    )
    _copy_file(ROOT / "packaging" / "AppRun", appdir / "AppRun", executable=True)
    _copy_file(
        ROOT / "packaging" / "appimage-env.sh",
        appdir / "usr" / "share" / "xlauncher" / "appimage-env.sh",
    )
    _copy_file(ROOT / "packaging" / "xlauncher.desktop", appdir / "xlauncher.desktop")
    icon = ROOT / "packaging" / "xlauncher.svg"
    _copy_file(icon, appdir / "xlauncher.svg")
    icon_directory = appdir / "usr" / "share" / "icons" / "hicolor"
    icon_directory.mkdir(parents=True, exist_ok=True)
    _copy_tree(Path("/usr/share/icons/hicolor"), icon_directory)
    _copy_file(
        icon,
        icon_directory / "scalable" / "apps" / "xlauncher.svg",
    )
    _write_dir_icon(appdir / ".DirIcon")
    adwaita_icons = Path("/usr/share/icons/Adwaita")
    if adwaita_icons.is_dir():
        _copy_tree(adwaita_icons, appdir / "usr" / "share" / "icons" / "Adwaita")
    gtk_data = Path("/usr/share/gtk-4.0")
    if gtk_data.is_dir():
        _copy_tree(gtk_data, appdir / "usr" / "share" / "gtk-4.0")
    adwaita_theme = Path("/usr/share/themes/Adwaita/gtk-4.0")
    if adwaita_theme.is_dir():
        _copy_tree(adwaita_theme, appdir / "usr" / "share" / "themes" / "Adwaita" / "gtk-4.0")

    schema_source = Path("/usr/share/glib-2.0/schemas")
    schema_destination = appdir / "usr" / "share" / "glib-2.0" / "schemas"
    _copy_tree(schema_source, schema_destination)
    _run(["glib-compile-schemas", "--strict", str(schema_destination)])


def _write_dir_icon(destination: Path) -> None:
    size = 256
    radius = 40
    stroke_radius = 12
    first = (60, 60)
    second = (196, 196)
    third = (196, 60)
    fourth = (60, 196)

    def distance_to_segment(point: tuple[int, int], start: tuple[int, int], end: tuple[int, int]) -> float:
        x, y = point
        start_x, start_y = start
        end_x, end_y = end
        dx = end_x - start_x
        dy = end_y - start_y
        fraction = max(
            0.0,
            min(1.0, ((x - start_x) * dx + (y - start_y) * dy) / (dx * dx + dy * dy)),
        )
        return ((x - start_x - fraction * dx) ** 2 + (y - start_y - fraction * dy) ** 2) ** 0.5

    rows = bytearray()
    for y in range(size):
        rows.append(0)
        for x in range(size):
            nearest_x = min(max(x, radius), size - radius - 1)
            nearest_y = min(max(y, radius), size - radius - 1)
            inside = (x - nearest_x) ** 2 + (y - nearest_y) ** 2 <= radius**2
            on_cross = min(
                distance_to_segment((x, y), first, second),
                distance_to_segment((x, y), third, fourth),
            ) <= stroke_radius
            rows.extend((255, 255, 255, 255) if on_cross else (0, 0, 0, 255 if inside else 0))

    def chunk(name: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )

    image = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(image)


def _copy_dependencies(appdir: Path, sources: set[Path]) -> None:
    destination = appdir / "usr" / "lib" / "x86_64-linux-gnu"
    destination.mkdir(parents=True, exist_ok=True)
    for source in sorted(sources):
        if source.is_file():
            target = destination / source.name
            if target.exists():
                if target.read_bytes() != source.read_bytes():
                    raise RuntimeError(
                        f"Farklı sistem kütüphaneleri aynı ada sahip: {source.name}"
                    )
                continue
            _copy_file(source, target)


def _write_third_party_notices(appdir: Path, files: set[Path]) -> None:
    packages: set[str] = set()
    for path in files:
        result = subprocess.run(
            ["dpkg-query", "-S", str(path)],
            check=False,
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            package = line.split(":", maxsplit=1)[0].strip()
            if package:
                packages.add(package)
    source_notice = ROOT / "packaging" / "THIRD_PARTY_NOTICES.md"
    rows = source_notice.read_text(encoding="utf-8").splitlines() + [
        "",
        "## Bu pakette bulunan sistem bileşenleri",
        "",
    ]
    documentation = appdir / "usr" / "share" / "doc" / "third-party"
    for package in sorted(packages):
        result = subprocess.run(
            ["dpkg-query", "-W", "-f=${binary:Package}\t${Version}", package],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode:
            continue
        rows.append(f"- `{result.stdout.strip()}`")
        package_name = package.split(":", maxsplit=1)[0]
        copyright = Path("/usr/share/doc") / package_name / "copyright"
        if copyright.is_file():
            _copy_file(copyright, documentation / package_name / "copyright")
    if not packages:
        rows.append("- Bileşen paketleri dpkg-query ile belirlenemedi.")
    notices = appdir / "usr" / "share" / "doc" / "xlauncher" / "THIRD_PARTY_NOTICES.md"
    notices.parent.mkdir(parents=True, exist_ok=True)
    notices.write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_appdir(destination: Path) -> None:
    if sys.platform != "linux" or platform.machine() not in {"x86_64", "amd64"}:
        raise RuntimeError("AppImage derlemesi yalnızca Linux x86_64 üzerinde desteklenir.")
    if os.geteuid() == 0:
        raise PermissionError("AppImage AppDir oluşturucusu root olarak çalıştırılamaz.")
    if destination.exists() and any(destination.iterdir()):
        raise FileExistsError(f"Hedef dizin boş değil: {destination}")
    destination.mkdir(parents=True, exist_ok=True)

    import gi

    for namespace, version in (
        ("Gtk", "4.0"),
        ("Gdk", "4.0"),
        ("Gio", "2.0"),
        ("GioUnix", "2.0"),
    ):
        gi.require_version(namespace, version)
    from gi.repository import Gdk, Gio, GioUnix, Gtk

    _ = Gdk, Gio, GioUnix, Gtk
    _copy_resources(destination)
    _copy_typelibs(destination)
    runtime_roots = _copy_python_runtime(destination)
    runtime_roots.extend(_find_required_libraries())
    runtime_roots.extend(_copy_gtk_runtime(destination))
    dependencies = _dependency_closure(runtime_roots)
    _copy_dependencies(destination, dependencies)
    _write_third_party_notices(destination, set(runtime_roots) | dependencies)


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} APPDIR", file=sys.stderr)
        return 2
    try:
        build_appdir(Path(sys.argv[1]).resolve())
    except (FileNotFoundError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"AppDir oluşturulamadı: {error}", file=sys.stderr)
        return 1
    print(f"AppDir hazır: {sys.argv[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
