# X-Launcher — AI Assistant Project Brief

> Give this document and the repository to another coding assistant as project
> context. The source and tests are authoritative if this brief becomes stale.

## Copy/paste task instructions

```text
You are helping maintain X-Launcher, a personal Linux desktop application
launcher written in Python with GTK4/PyGObject. Read this brief and inspect the
relevant source and tests before changing code. Preserve the modular design,
GTK4-only APIs, Turkish user-facing messages, current behavior, and explicit
error reporting. Make a focused implementation, add regression tests, run the
relevant checks, and update README.md and this brief when user-visible behavior
or installation changes.

Never use eval() for calculator input, shell execution for desktop launch or
web search, or GTK3 APIs. Launch desktop entries through Gio,
open web addresses through Gio.AppInfo.launch_default_for_uri(), and use
Gdk.Display.get_default().get_clipboard().set_text() for GTK4 clipboard writes.
Do not claim Wayland guarantees window position or focus. Do not claim AppImage
compatibility beyond its unvalidated Ubuntu Jammy amd64 recipe.

Explain changed files and verified test results. Do not claim GUI behavior,
builds, or platform compatibility that was not actually tested.
```

## Purpose and current behavior

X-Launcher is a small, borderless GTK4 launcher for Linux desktops, especially
GNOME/Wayland. Its window is about 600×60 pixels when idle, uses a dark CSS
theme, and grows to display search results. The window is launched or toggled
by a user-level Unix-socket daemon; GNOME, not the application, owns global
keyboard shortcuts.

### Query modes

The router checks exact case-insensitive aliases first, then handles:

| Input | Behavior |
|---|---|
| `firefox` | Fuzzy-search installed, visible `.desktop` applications |
| `= (5 + 3) * 2` | Safely evaluate arithmetic using a restricted AST |
| `g Python GTK`, `ddg Python GTK`, `br GTK`, `yt GTK`, `gh GTK` | Search Google, DuckDuckGo, Brave, YouTube, or GitHub |
| `s GTK` | Search with the configured default engine |
| `25 km to mile` | Convert supported units using `Decimal` |
| `time`, `today`, `date` | Display local time or date |
| `cb` | List text explicitly copied from X-Launcher |
| `cb clear` | Ask before clearing X-Launcher clipboard history |
| an exact configured alias | Launch a desktop ID or open a validated HTTP(S) URL |

`↑`/`↓` navigate results, `Enter` activates the selection, and `Escape` hides
the launcher. `Ctrl+D` toggles the selected app's favorite state, `Ctrl+R`
refreshes the app catalog, and `Ctrl+,` opens preferences. Launch/copy errors
and other user-facing status messages are in Turkish.

## Runtime and dependencies

- Python 3.10 or later; standard library only beyond system GTK packages.
- GTK4 and PyGObject, including Gio/GioUnix introspection typelibs.
- The application discovers desktop entries using `Gio.AppInfo.get_all()` and
  `GioUnix.DesktopAppInfo.should_show()`.
- App discovery runs asynchronously; results are returned to GTK through the
  GLib main loop. A configured polling interval can refresh the catalog.
- Wayland may constrain focus and placement. `present()` and `grab_focus()` are
  requests, not guarantees.
- All user data is local. The clipboard history records only text copied
  explicitly inside X-Launcher and does not monitor the system clipboard.

## Modules

| File | Responsibility |
|---|---|
| `main.py` | GTK application/window, routing, result activation, keyboard controls, refresh and file watching |
| `desktop_parser.py` | Discover visible Gio desktop apps and expose search metadata |
| `fuzzy_search.py` | Unicode/diacritic normalization, typo-tolerant matching, stable ranking |
| `command_router.py` | Classify aliases, calculator, web, clipboard and local provider queries |
| `calculator.py` | Restricted AST arithmetic; never use Python `eval()` |
| `providers.py` | Local date/time and Decimal unit conversions |
| `web_search.py` | URL-encoded search URIs, known search engines, validated HTTP(S) opening |
| `app_launcher.py` | Launch a retained Gio desktop-entry object without shell parsing |
| `config_manager.py` | Validated central settings and atomic private JSON writes |
| `history_manager.py` | Recent app IDs, timestamps, usage counts, time/frequency ranking |
| `favorites_manager.py` | Persist and validate favorite desktop IDs |
| `clipboard_history.py` | Persist explicitly copied text only |
| `alias_manager.py` | Load, validate, resolve and save app/web aliases |
| `theme_manager.py` | Load/validate user GTK CSS; use built-in dark CSS on failure |
| `preferences_window.py` | GTK4 preferences for search, appearance, aliases and local data |
| `toggle_daemon.py` | Private Unix-socket server/client, toggle, stop and reload commands |
| `version.py` | Application ID, display name and version |
| `install.sh`, `uninstall.sh` | User-level installation and code-only removal |
| `scan_bugs.py` | Structural checks plus unittest discovery (not a full static analyzer) |

## Search and launch flow

1. `main.py` passes the query, an exact alias if present, and the configured
   default engine to `command_router.route_query()`.
2. Application queries go to `fuzzy_search.search_applications()`. Ranking
   considers display name, generic name, executable, desktop ID, keywords,
   categories and comment; favorites and optional recent-use scores are small
   boosts. Results are capped by the configured limit.
3. Empty queries can show favorites and recently launched apps according to
   preferences.
4. Gio icons are rendered by GTK4 `Gtk.Image`; a generic icon is used when the
   desktop entry provides none.
5. App activation calls `app_launcher.launch_application()`, which launches the
   original `GioUnix.DesktopAppInfo`. A successful launch updates history.
6. Calculator, clipboard and provider outputs use
   `Gdk.Display.get_default().get_clipboard().set_text()` when copied. Web
   results open via `Gio.AppInfo.launch_default_for_uri()`.
7. Exceptions and false launch results must stay visible in the Turkish status
   label; do not convert failures into success-shaped fallbacks.

## User configuration and privacy

The data root is `$XDG_DATA_HOME/xlauncher/`, or
`~/.local/share/xlauncher/` when `XDG_DATA_HOME` is unset:

- `config.json`: theme, search engine, ranking/display options, result/history
  limits, polling interval, and clipboard-history options.
- `aliases.json`: one-word aliases with `app` desktop IDs or validated `web`
  HTTP(S) URLs.
- `history.json`: unique desktop IDs with `last_used` timestamps and
  `use_count`.
- `favorites.json`: favorited desktop IDs.
- `clipboard_history.json`: explicitly copied strings, bounded by configured
  count.
- `themes/<name>/theme.css`: user GTK4 CSS; theme name is constrained to one
  safe directory component.

Settings and data writes use atomic replacement and restrictive permissions
where applicable. Missing/corrupt optional data should not crash the launcher;
log errors and retain sensible prior/default state. Do not silently hide actual
write/launch failures. Never add clipboard polling or network transmission of
local history.

## Daemon and CLI

The daemon socket is `$XDG_RUNTIME_DIR/xlauncher/control.sock`, inside a
user-owned private directory. It validates socket ownership and file type,
probes an existing socket before stale-socket cleanup, and removes only its own
socket inode on shutdown. Socket-thread UI callbacks must use `GLib.idle_add()`.

Commands:

```text
xlauncher --toggle
xlauncher --reload
xlauncher --reload-apps
xlauncher --stop
xlauncher --version
```

On Wayland, a GNOME custom shortcut should invoke `xlauncher`; do not implement
global key capture in the Python process. Reload commands start a daemon if
needed. Avoid arbitrary shell command protocols over the socket.

## Install, test, and package

The primary supported install is the native user-level `./install.sh`; it
installs the executable, Python modules, desktop entry and icon without sudo.
`xlauncher-uninstall` removes application code/desktop integration while
preserving user settings, history, aliases, clipboard data and custom themes.

Ubuntu/Debian system dependencies:

```bash
sudo apt install python3-gi gir1.2-gtk-4.0
```

Developer checks:

```bash
python3 -m unittest discover -s tests -v
python3 scan_bugs.py
bash -n install.sh
bash -n uninstall.sh
```

GitHub Actions runs tests and source/script validation on Ubuntu 24.04 with GTK4
bindings. Tests cover calculator safety, fuzzy ranking, settings, history,
favorites, clipboard, aliases, providers, themes, daemon sockets and install/
uninstall behavior. A passing headless unit suite does not verify visual
behavior on every Wayland compositor.

AppImage packaging is **experimental and unmaintained**. Its current recipe
targets Ubuntu Jammy amd64 and is not validated on newer Ubuntu/GNOME/Python/
GTK releases. Do not present it as a tested installation option; prefer
`./install.sh`.

## Design and change constraints

- Preserve separation of concerns and existing public helpers; search for
  prior art before adding parallel logic.
- Keep GTK APIs GTK4-only, UI messages in Turkish, and Python types accurate.
- Do not use shell execution for application launch or web query handling.
- Do not weaken URL validation, socket ownership checks, permission checks or
  calculator limits.
- Add focused tests and update documentation for behavior changes.
- Keep AppImage and Wayland capability claims strictly evidence-based.
- No license file currently exists; do not claim a license.
