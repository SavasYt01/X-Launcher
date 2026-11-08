"""Build Gio launch contexts that keep AppImage runtime paths out of host apps."""

import os

import gi

gi.require_version("Gio", "2.0")
from gi.repository import Gio


_APPIMAGE_HOST_ENVIRONMENT = (
    "LD_LIBRARY_PATH",
    "PYTHONPATH",
    "PYTHONHOME",
    "GI_TYPELIB_PATH",
    "GSETTINGS_SCHEMA_DIR",
    "GDK_PIXBUF_MODULE_FILE",
    "GTK_PATH",
    "GIO_MODULE_DIR",
    "XDG_DATA_DIRS",
    "PATH",
)


def create_app_launch_context() -> Gio.AppLaunchContext | None:
    """Create a launch context with the original host environment in AppImages."""
    if os.environ.get("XLAUNCHER_APPIMAGE_RUNTIME") != "1":
        return None
    context = Gio.AppLaunchContext()

    for variable in _APPIMAGE_HOST_ENVIRONMENT:
        suffix = variable.replace("-", "_")
        was_set = os.environ.get(f"XLAUNCHER_HOST_ENV_SET_{suffix}") == "1"
        original_value = os.environ.get(f"XLAUNCHER_HOST_ENV_VALUE_{suffix}", "")
        if was_set:
            context.setenv(variable, original_value)
        else:
            context.unsetenv(variable)

    metadata = (
        "APPDIR",
        "APPIMAGE",
        "XLAUNCHER_APPIMAGE_RUNTIME",
        "XLAUNCHER_HOST_ENV_SET_APPIMAGE",
        "XLAUNCHER_HOST_ENV_VALUE_APPIMAGE",
        *(
            name
            for variable in _APPIMAGE_HOST_ENVIRONMENT
            for name in (
                f"XLAUNCHER_HOST_ENV_SET_{variable.replace('-', '_')}",
                f"XLAUNCHER_HOST_ENV_VALUE_{variable.replace('-', '_')}",
            )
        ),
    )
    for variable in metadata:
        context.unsetenv(variable)
    return context
