"""Offline, standard-library-first environment diagnostics."""

import importlib.util
import os
import platform
import socket
import stat
import sys
from pathlib import Path

from version import APP_NAME, VERSION


_MODULES = (
    "main",
    "app_launcher",
    "desktop_parser",
    "fuzzy_search",
    "command_router",
    "calculator",
    "providers",
    "web_search",
    "config_manager",
    "history_manager",
    "favorites_manager",
    "clipboard_history",
    "alias_manager",
    "theme_manager",
    "preferences_window",
    "toggle_daemon",
    "help_content",
    "doctor",
    "appimage_integration",
    "launcher_cli",
    "app_launch_context",
    "version",
)


def _data_directory() -> Path:
    data_home = Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )
    return data_home / "xlauncher"


def _report(state: str, label: str, detail: str) -> None:
    print(f"{state} {label}: {detail}")


def _writable_directory(path: Path) -> Path | None:
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    if not candidate.is_dir() or not os.access(candidate, os.W_OK | os.X_OK):
        return None
    return candidate


def _python_version_supported(major: int, minor: int) -> bool:
    return (major, minor) >= (3, 10)


def run() -> int:
    """Print diagnostics without opening a GUI or using the network."""
    failures = 0
    warnings = 0
    root = Path(__file__).resolve().parent
    data_dir = _data_directory()
    config_path = data_dir / "config.json"
    print(f"{APP_NAME} {VERSION} — sistem tanılaması (ağ bağlantısı kullanılmaz)")
    _report("✅", "Python", platform.python_version())
    if not _python_version_supported(sys.version_info.major, sys.version_info.minor):
        _report("❌", "Python sürümü", "Python 3.10 veya üzeri gereklidir.")
        failures += 1
    else:
        _report("✅", "Python sürümü", "gereksinim karşılanıyor.")

    try:
        import gi

        _report("✅", "PyGObject", str(getattr(gi, "__version__", "içe aktarma başarılı")))
    except (ImportError, OSError) as error:
        _report("❌", "PyGObject", str(error))
        failures += 1
    else:
        for namespace, version in (
            ("Gtk", "4.0"),
            ("Gdk", "4.0"),
            ("Gio", "2.0"),
            ("GioUnix", "2.0"),
            ("GLib", "2.0"),
            ("GObject", "2.0"),
            ("Pango", "1.0"),
        ):
            try:
                gi.require_version(namespace, version)
                repository = __import__("gi.repository", fromlist=[namespace])
                getattr(repository, namespace)
            except (ImportError, ValueError, OSError) as error:
                _report("❌", f"{namespace} typelib", str(error))
                failures += 1
            else:
                _report("✅", f"{namespace} typelib", f"{version} kullanılabilir.")

    architecture = platform.machine()
    if architecture in {"x86_64", "amd64"}:
        _report("✅", "Mimari", architecture)
    else:
        _report("⚠️", "Mimari", f"{architecture}; AppImage x86_64 için hazırlanır.")
        warnings += 1

    _report(
        "✅" if os.environ.get("XDG_CURRENT_DESKTOP") else "⚠️",
        "Masaüstü ortamı",
        os.environ.get("XDG_CURRENT_DESKTOP", "belirlenmemiş"),
    )
    _report(
        "✅" if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY") else "⚠️",
        "Görüntü oturumu",
        os.environ.get("XDG_SESSION_TYPE")
        or (
            "Wayland"
            if os.environ.get("WAYLAND_DISPLAY")
            else "X11"
            if os.environ.get("DISPLAY")
            else "grafik arayüz yok"
        ),
    )

    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        runtime_path = Path(runtime)
        try:
            runtime_info = runtime_path.stat()
            valid_runtime = (
                stat.S_ISDIR(runtime_info.st_mode)
                and runtime_info.st_uid == os.getuid()
            )
        except OSError as error:
            valid_runtime = False
            runtime_detail = str(error)
        else:
            runtime_detail = str(runtime_path)
        _report("✅" if valid_runtime else "⚠️", "XDG_RUNTIME_DIR", runtime_detail)
        if not valid_runtime:
            warnings += 1
    else:
        _report("⚠️", "XDG_RUNTIME_DIR", "ayarlanmamış; daemon çalışmayabilir.")
        warnings += 1

    _report("ℹ️", "Kullanıcı verisi", str(data_dir))
    if config_path.exists():
        try:
            config_path.read_bytes()
        except OSError as error:
            _report("❌", "Ayarları okuma", str(error))
            failures += 1
        else:
            _report("✅", "Ayarları okuma", "erişilebilir.")
    else:
        _report("ℹ️", "Ayarları okuma", "dosya yok; varsayılan ayarlar kullanılacak.")
    writable = _writable_directory(data_dir)
    if writable is None:
        _report("⚠️", "Veri yazma", "üst dizine yazılamıyor.")
        warnings += 1
    else:
        _report("✅", "Veri yazma", f"{writable} yazılabilir.")

    appimage = os.environ.get("APPIMAGE")
    if appimage:
        image_path = Path(appimage)
        exists = image_path.is_file() and os.access(image_path, os.X_OK)
        _report("✅" if exists else "❌", "AppImage dosyası", str(image_path))
        if not exists:
            failures += 1
    else:
        _report("ℹ️", "AppImage ortamı", "AppImage dışından çalışıyor (yerel kurulum veya AppDir).")

    theme_path = root / "themes" / "default-dark" / "theme.css"
    _report(
        "✅" if theme_path.is_file() else "⚠️",
        "Varsayılan tema",
        str(theme_path) if theme_path.is_file() else "paket içi CSS bulunamadı.",
    )
    if not theme_path.is_file():
        warnings += 1

    module_paths = []
    for module in _MODULES:
        try:
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            available = False
        if available:
            module_paths.append(module)
    missing = sorted(set(_MODULES) - set(module_paths))
    if missing:
        _report("⚠️", "Uygulama modülleri", f"eksik: {', '.join(missing)}")
        warnings += 1
    else:
        _report("✅", "Uygulama modülleri", f"{len(module_paths)} modül kullanılabilir.")

    if runtime and Path(runtime).is_dir():
        socket_path = Path(runtime) / "xlauncher" / "control.sock"
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.settimeout(0.25)
        try:
            client.connect(str(socket_path))
        except FileNotFoundError:
            _report("ℹ️", "Daemon soketi", "çalışan daemon bulunamadı.")
        except (ConnectionRefusedError, OSError) as error:
            _report("⚠️", "Daemon soketi", f"bağlantı kurulamadı: {error}")
            warnings += 1
        else:
            _report("✅", "Daemon soketi", "çalışıyor.")
        finally:
            client.close()
    else:
        _report("⚠️", "Daemon soketi", "XDG_RUNTIME_DIR bulunamadı.")
        warnings += 1

    print(f"\nSonuç: {failures} hata, {warnings} uyarı.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
