xlauncher_prepare_environment() {
    if [ "${LD_LIBRARY_PATH+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_LD_LIBRARY_PATH=1
        export XLAUNCHER_HOST_ENV_VALUE_LD_LIBRARY_PATH=$LD_LIBRARY_PATH
    else
        unset XLAUNCHER_HOST_ENV_SET_LD_LIBRARY_PATH XLAUNCHER_HOST_ENV_VALUE_LD_LIBRARY_PATH
    fi
    if [ "${PYTHONPATH+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_PYTHONPATH=1
        export XLAUNCHER_HOST_ENV_VALUE_PYTHONPATH=$PYTHONPATH
    else
        unset XLAUNCHER_HOST_ENV_SET_PYTHONPATH XLAUNCHER_HOST_ENV_VALUE_PYTHONPATH
    fi
    if [ "${PYTHONHOME+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_PYTHONHOME=1
        export XLAUNCHER_HOST_ENV_VALUE_PYTHONHOME=$PYTHONHOME
    else
        unset XLAUNCHER_HOST_ENV_SET_PYTHONHOME XLAUNCHER_HOST_ENV_VALUE_PYTHONHOME
    fi
    if [ "${GI_TYPELIB_PATH+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_GI_TYPELIB_PATH=1
        export XLAUNCHER_HOST_ENV_VALUE_GI_TYPELIB_PATH=$GI_TYPELIB_PATH
    else
        unset XLAUNCHER_HOST_ENV_SET_GI_TYPELIB_PATH XLAUNCHER_HOST_ENV_VALUE_GI_TYPELIB_PATH
    fi
    if [ "${GSETTINGS_SCHEMA_DIR+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_GSETTINGS_SCHEMA_DIR=1
        export XLAUNCHER_HOST_ENV_VALUE_GSETTINGS_SCHEMA_DIR=$GSETTINGS_SCHEMA_DIR
    else
        unset XLAUNCHER_HOST_ENV_SET_GSETTINGS_SCHEMA_DIR XLAUNCHER_HOST_ENV_VALUE_GSETTINGS_SCHEMA_DIR
    fi
    if [ "${GDK_PIXBUF_MODULE_FILE+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_GDK_PIXBUF_MODULE_FILE=1
        export XLAUNCHER_HOST_ENV_VALUE_GDK_PIXBUF_MODULE_FILE=$GDK_PIXBUF_MODULE_FILE
    else
        unset XLAUNCHER_HOST_ENV_SET_GDK_PIXBUF_MODULE_FILE XLAUNCHER_HOST_ENV_VALUE_GDK_PIXBUF_MODULE_FILE
    fi
    if [ "${GTK_PATH+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_GTK_PATH=1
        export XLAUNCHER_HOST_ENV_VALUE_GTK_PATH=$GTK_PATH
    else
        unset XLAUNCHER_HOST_ENV_SET_GTK_PATH XLAUNCHER_HOST_ENV_VALUE_GTK_PATH
    fi
    if [ "${GIO_MODULE_DIR+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_GIO_MODULE_DIR=1
        export XLAUNCHER_HOST_ENV_VALUE_GIO_MODULE_DIR=$GIO_MODULE_DIR
    else
        unset XLAUNCHER_HOST_ENV_SET_GIO_MODULE_DIR XLAUNCHER_HOST_ENV_VALUE_GIO_MODULE_DIR
    fi
    if [ "${XDG_DATA_DIRS+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_XDG_DATA_DIRS=1
        export XLAUNCHER_HOST_ENV_VALUE_XDG_DATA_DIRS=$XDG_DATA_DIRS
    else
        unset XLAUNCHER_HOST_ENV_SET_XDG_DATA_DIRS XLAUNCHER_HOST_ENV_VALUE_XDG_DATA_DIRS
    fi
    if [ "${PATH+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_PATH=1
        export XLAUNCHER_HOST_ENV_VALUE_PATH=$PATH
    else
        unset XLAUNCHER_HOST_ENV_SET_PATH XLAUNCHER_HOST_ENV_VALUE_PATH
    fi
    if [ "${APPIMAGE+x}" ]; then
        export XLAUNCHER_HOST_ENV_SET_APPIMAGE=1
        export XLAUNCHER_HOST_ENV_VALUE_APPIMAGE=$APPIMAGE
    else
        unset XLAUNCHER_HOST_ENV_SET_APPIMAGE XLAUNCHER_HOST_ENV_VALUE_APPIMAGE
    fi

    export XLAUNCHER_APPIMAGE_RUNTIME=1
    export PYTHONHOME="$APPDIR/usr"
    export PYTHONPATH="$APPDIR/usr/bin:$APPDIR/usr/lib/python3/dist-packages"
    export PATH="$APPDIR/usr/bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"
    export LD_LIBRARY_PATH="$APPDIR/usr/lib/x86_64-linux-gnu:$APPDIR/usr/lib"
    export GI_TYPELIB_PATH="$APPDIR/usr/lib/x86_64-linux-gnu/girepository-1.0:$APPDIR/usr/lib/girepository-1.0"
    export GIO_MODULE_DIR="$APPDIR/usr/lib/x86_64-linux-gnu/gio/modules"
    export XDG_DATA_DIRS="$APPDIR/usr/share:${XDG_DATA_DIRS:-/usr/local/share:/usr/share}"
    export GSETTINGS_SCHEMA_DIR="$APPDIR/usr/share/glib-2.0/schemas"

}

xlauncher_prepare_pixbuf_cache() {
    loader_template="$APPDIR/usr/share/xlauncher/gdk-pixbuf-loaders.cache"
    if [ ! -f "$loader_template" ]; then
        printf 'X-Launcher: GdkPixbuf yükleyici tanımı bulunamadı.\n' >&2
        return 1
    fi
    cache_home=${XDG_CACHE_HOME:-"${HOME:-/tmp}/.cache"}
    cache_key=$(printf '%s' "${APPIMAGE:-$APPDIR}:$APPDIR" | cksum | cut -d ' ' -f 1)
    cache_directory="$cache_home/xlauncher"
    cache_file="$cache_directory/gdk-pixbuf-loaders-$cache_key.cache"
    if ! mkdir -p "$cache_directory" 2>/dev/null; then
        printf 'X-Launcher: Önbellek dizinine yazılamıyor: %s\n' "$cache_directory" >&2
        return 1
    fi
    if [ ! -f "$cache_file" ] || [ "$loader_template" -nt "$cache_file" ]; then
        temporary_cache=$(mktemp "$cache_file.XXXXXX") || {
            printf 'X-Launcher: GdkPixbuf önbelleği oluşturulamadı.\n' >&2
            return 1
        }
        if "$APPDIR/usr/bin/python3" -c \
            'from pathlib import Path; import sys; Path(sys.argv[2]).write_text(Path(sys.argv[1]).read_text(encoding="utf-8").replace("@APPDIR@", sys.argv[3]), encoding="utf-8")' \
            "$loader_template" "$temporary_cache" "$APPDIR" &&
            mv -f -- "$temporary_cache" "$cache_file"; then
            chmod 0600 "$cache_file"
        fi
        if [ ! -f "$cache_file" ]; then
            rm -f -- "$temporary_cache"
            printf 'X-Launcher: GdkPixbuf önbelleği yazılamadı.\n' >&2
            return 1
        fi
    fi
    export GDK_PIXBUF_MODULE_FILE="$cache_file"
}
