"""Explicit, user-scoped desktop integration for an AppImage."""

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path


_DESKTOP_NAME = "xlauncher-appimage.desktop"
_ICON_NAME = "xlauncher-appimage.svg"
_MARKER = "X-XLauncher-Managed=true"


def _data_home() -> Path:
    return Path(
        os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
    )


def _appimage_path(environment: dict[str, str] | None = None) -> Path:
    env = os.environ if environment is None else environment
    appimage = env.get("APPIMAGE")
    if not appimage:
        raise RuntimeError("Bu komut yalnızca AppImage içinden çalıştırılabilir.")
    image = Path(appimage).expanduser().resolve()
    if not image.is_file() or not os.access(image, os.X_OK):
        raise RuntimeError(
            f"AppImage dosyası bulunamadı veya çalıştırılabilir değil: {image}. "
            "Dosya taşındıysa entegrasyonu yeni konumdan yeniden çalıştırın."
        )
    return image


def _desktop_quote(value: str) -> str:
    if any(ord(character) < 0x20 for character in value):
        raise ValueError("AppImage yolu kontrol karakteri içeremez.")
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("`", "\\`")
        .replace("$", "\\$")
        .replace("%", "%%")
    )
    return f'"{escaped}"'


def _ensure_user_directory(path: Path) -> Path:
    if os.geteuid() == 0:
        raise PermissionError("Masaüstü entegrasyonu root olarak çalıştırılamaz.")
    resolved = path.resolve()
    resolved.mkdir(parents=True, exist_ok=True, mode=0o755)
    return _validate_user_directory(resolved)


def _validate_user_directory(path: Path) -> Path:
    resolved = path.resolve()
    info = resolved.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise PermissionError(f"Kullanıcıya ait olmayan dizin reddedildi: {resolved}")
    return resolved


def _atomic_write(path: Path, content: bytes, mode: int = 0o644) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as file:
            os.fchmod(file.fileno(), mode)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, path)
    except OSError:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _icon_source(appdir: Path | None = None) -> Path:
    if appdir is None:
        value = os.environ.get("APPDIR")
        if not value:
            raise RuntimeError("AppImage çalışma dizini bulunamadı.")
        appdir = Path(value)
    source = (
        appdir
        / "usr"
        / "share"
        / "icons"
        / "hicolor"
        / "scalable"
        / "apps"
        / "xlauncher.svg"
    )
    if not source.is_file():
        raise RuntimeError(f"Paket içi simge bulunamadı: {source}")
    return source


def desktop_entry_text(image_path: Path, icon_name: str = "xlauncher-appimage") -> str:
    """Create the AppImage desktop file using freedesktop Exec quoting."""
    executable = _desktop_quote(str(image_path))
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        "Name=X-Launcher\n"
        "Comment=Hızlı ve modern uygulama başlatıcı\n"
        f"Exec={executable} --toggle\n"
        f"Icon={icon_name}\n"
        "Categories=Utility;\n"
        "Terminal=false\n"
        "StartupNotify=false\n"
        f"{_MARKER}\n"
    )


def integrate(
    environment: dict[str, str] | None = None,
    appdir: Path | None = None,
) -> int:
    try:
        image = _appimage_path(environment)
        data_home = _ensure_user_directory(_data_home())
        applications = _ensure_user_directory(data_home / "applications")
        icon_directory = _ensure_user_directory(
            data_home / "icons" / "hicolor" / "scalable" / "apps"
        )
        desktop_path = applications / _DESKTOP_NAME
        icon_path = icon_directory / _ICON_NAME
        icon_content = _icon_source(appdir).read_bytes()

        if desktop_path.exists():
            existing = desktop_path.read_text(encoding="utf-8")
            if _MARKER not in existing:
                raise FileExistsError(
                    f"İlgisiz masaüstü girdisinin üzerine yazılmayacak: {desktop_path}"
                )
        if icon_path.exists() and icon_path.read_bytes() != icon_content:
            raise FileExistsError(
                f"İlgisiz simge dosyasının üzerine yazılmayacak: {icon_path}"
            )

        desktop_content = desktop_entry_text(image).encode("utf-8")
        temporary_desktop: Path | None = None
        icon_created = not icon_path.exists()
        try:
            descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{desktop_path.name}.",
                suffix=".desktop",
                dir=applications,
            )
            temporary_desktop = Path(temporary_name)
            with os.fdopen(descriptor, "wb") as file:
                os.fchmod(file.fileno(), 0o644)
                file.write(desktop_content)

            validator = shutil.which("desktop-file-validate")
            if validator:
                validation = subprocess.run(
                    [validator, str(temporary_desktop)],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if validation.returncode:
                    raise ValueError(
                        f"Masaüstü girdisi doğrulanamadı: {validation.stderr.strip()}"
                    )

            if icon_created:
                _atomic_write(icon_path, icon_content)
            os.replace(temporary_desktop, desktop_path)
        except (OSError, ValueError):
            if icon_created:
                icon_path.unlink(missing_ok=True)
            raise
        finally:
            if temporary_desktop is not None:
                temporary_desktop.unlink(missing_ok=True)
        print(
            "X-Launcher uygulama menüsüne eklendi. AppImage taşınırsa "
            "yeni konumdan --integrate komutunu yeniden çalıştırın."
        )
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        print(f"X-Launcher entegrasyonu başarısız: {error}", file=os.sys.stderr)
        return 1


def unintegrate() -> int:
    try:
        if os.geteuid() == 0:
            raise PermissionError("Masaüstü entegrasyonu root olarak kaldırılamaz.")
        data_home_path = _data_home()
        if not data_home_path.exists():
            print("X-Launcher AppImage entegrasyonu bulunamadı.")
            return 0
        data_home = _validate_user_directory(data_home_path)
        applications_directory = data_home / "applications"
        if not applications_directory.exists():
            print("X-Launcher AppImage entegrasyonu bulunamadı.")
            return 0
        applications_directory = _validate_user_directory(applications_directory)
        desktop_path = applications_directory / _DESKTOP_NAME
        icon_path = (
            data_home / "icons" / "hicolor" / "scalable" / "apps" / _ICON_NAME
        )
        if not desktop_path.is_file():
            print("X-Launcher AppImage entegrasyonu bulunamadı.")
            return 0
        content = desktop_path.read_text(encoding="utf-8")
        if _MARKER not in content:
            raise PermissionError(
                f"Bu masaüstü girdisini X-Launcher oluşturmadı; korundu: {desktop_path}"
            )
        icon_source = _icon_source()
        icon_content = icon_source.read_bytes()
        remove_icon = False
        if icon_path.is_file():
            _validate_user_directory(icon_path.parent)
            remove_icon = icon_path.read_bytes() == icon_content
        elif icon_path.exists() or icon_path.is_symlink():
            _validate_user_directory(icon_path.parent)
        desktop_path.unlink()
        if remove_icon:
            icon_path.unlink()
        elif icon_path.exists() or icon_path.is_symlink():
            print(f"Kullanıcı tarafından değiştirilmiş simge korundu: {icon_path}")
        print("X-Launcher AppImage entegrasyonu kaldırıldı; yerel kurulum etkilenmedi.")
        return 0
    except (OSError, RuntimeError, UnicodeError, ValueError) as error:
        print(f"X-Launcher entegrasyonu kaldırılamadı: {error}", file=os.sys.stderr)
        return 1
