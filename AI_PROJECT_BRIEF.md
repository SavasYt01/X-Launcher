# X-Launcher — AI Assistant Project Brief

> **Use this document as context for another AI coding assistant.**
> Read it together with the source files before proposing or making changes.
> The repository is the source of truth if any detail here becomes stale.

## Copy/paste prompt

```text
You are helping develop X-Launcher, a personal Linux application launcher.
First inspect the repository and this project brief. Treat the current source
code and tests as authoritative; do not assume a reported bug is real until
you verify it in the code or reproduce it.

Work in small, reviewable changes. Preserve the existing modular architecture,
GTK4/PyGObject patterns, the Turkish user-facing messages, and the behavior of
existing search modes. Do not rewrite modules or add dependencies unless the
requested feature requires them. Before changing behavior, identify the
relevant code path and tests. Add focused tests for behavior changes and run
the smallest relevant validation, followed by the full unittest suite when
appropriate.

Important project facts:
- This is a GTK4 desktop GUI written in Python with PyGObject, not a terminal
  application.
- Installed applications are discovered through Gio.AppInfo and
  GioUnix.DesktopAppInfo; Gio performs desktop-entry handling and visibility
  filtering.
- Application launching uses DesktopAppInfo.launch(), not shell execution.
- Application-search queries use a small in-project fuzzy ranker.
- A query beginning with "=" invokes calculator.py. It uses a restricted AST
  evaluator; do not replace it with eval().
- A query beginning with "g " opens a URL-encoded Google search through the
  user's default browser. Do not execute the query as a shell command.
- Exact user aliases are loaded from `$XDG_DATA_HOME/xlauncher/aliases.json`
  (default `~/.local/share/xlauncher/aliases.json`) before calculator, web, or
  app-search routing. App aliases target desktop IDs; web aliases accept only
  HTTP(S) URLs.
- Successful application launches are recorded in
  `$XDG_DATA_HOME/xlauncher/history.json` (default
  `~/.local/share/xlauncher/history.json`); the last 20 unique apps receive a
  small fuzzy-search ranking boost.
- The optional toggle daemon receives commands over a per-user Unix socket.
  GTK mutations are marshalled onto the GLib main loop.
- Wayland controls window positioning and may deny focus requests. Do not
  claim that the application can guarantee screen centering or focus.
- Do not blindly add duplicate icon or stale-socket handling. App icons are
  represented as Gio.Icon and shown with Gtk.Image.new_from_gicon(). The daemon
  probes existing sockets, handles stale owned sockets, and has regression
  tests for live/replaced sockets.
- Application launch failures are reported in the launcher status label.
- The status label is placed below the results list so operation feedback
  appears at the bottom of the launcher window.
- GTK4 clipboard writes use `Gdk.ContentProvider.new_for_value()` and
  `Gdk.Clipboard.set_content()`; do not assume `Gdk.Clipboard.set_text()` is
  available in the installed PyGObject binding.
- AppImage packaging files exist, but an AppImage has not yet been built or
  validated. The current recipe targets Ubuntu Jammy amd64 and needs review
  before claiming compatibility with another target distribution.

For code changes, explain what changed, why it is correct, tests run and any
remaining limitation. Do not say that an unrun build or GUI behavior was
verified.
```

## Project at a glance

X-Launcher is a personal launcher for Linux desktop sessions. It provides a
small, dark GTK4 window for searching desktop applications, plus two prefixed
query modes:

| Input | Meaning | Action |
|---|---|---|
| `firefox` | Search installed desktop applications | Select a result and press Enter to launch |
| `= (5 + 3) * 2` | Calculate arithmetic | Select the result and press Enter to copy it |
| `g python GTK Wayland` | Search the web | Select the result and press Enter to open the default browser |
| `yt` | Resolve a configured alias | Open its HTTP(S) URL or launch its desktop application |

The window supports `Up`, `Down`, `Enter`, and `Escape`. A separate optional
daemon and command-line toggle entrypoint allow GNOME to invoke the launcher
through a custom keyboard shortcut on Wayland.

## User and platform context

- **Intended environment:** Linux desktop, particularly Ubuntu with GNOME and
  Wayland. The original target description specified Ubuntu 26.04, GNOME 50.1,
  Mutter/Wayland, Zsh, and Ptyxis.
- **Language/runtime:** Python 3.
- **GUI:** GTK4 through PyGObject.
- **Desktop integration:** Gio/GioUnix and freedesktop `.desktop` entries.
- **Visual target:** black `#000000` surface, white `#ffffff` text, SF Pro
  Display at 16pt when installed, borderless window, 12px corners, subtle
  shadow, and a 600×60 default size.
- **Dependencies:** Python standard library plus system-provided PyGObject,
  GTK4, and their GI typelibs. There is no Python package manifest in the
  current project.

The environment that previously ran the checks reported `/usr/bin/python3`
with Python 3.14, GTK 4.22, and a Wayland display. That is an observation about
the development environment, not a promise that every target system has the
same versions.

## Repository layout

```text
.
├── main.py
├── desktop_parser.py
├── fuzzy_search.py
├── history_manager.py
├── alias_manager.py
├── calculator.py
├── web_search.py
├── app_launcher.py
├── toggle_daemon.py
├── xlauncher-toggle
├── install.sh
├── scan_bugs.py
├── tests/
│   ├── test_calculator.py
│   ├── test_fuzzy_search.py
│   ├── test_history.py
│   ├── test_aliases.py
│   ├── test_install.py
│   ├── test_toggle_daemon.py
│   └── test_web_search.py
├── packaging/
│   ├── AppImageBuilder.yml
│   ├── AppRun
│   ├── xlauncher.desktop
│   └── xlauncher.svg
└── scripts/
    └── build-appimage.sh
```

## Module responsibilities

### `main.py` — application and GTK interface

`XLauncher` subclasses `Gtk.Application`. It creates the undecorated GTK4
window, installs application CSS, connects the entry's `changed` and `activate`
signals, displays result rows and handles keyboard navigation.

The `results` collection contains four result types:

- `DesktopApplication` for installed desktop apps
- `CalculationResult` for arithmetic results
- `WebSearchResult` for a web search request
- `Alias` for a web URL alias

`_on_search_changed()` is the query router. It checks an exact alias first,
then calculator syntax, the `g ` web-search prefix, and finally application
fuzzy search. App aliases resolve to an installed desktop ID and use the
normal launch path; web aliases are opened through Gio. When the query changes,
the result list is rebuilt and the first row is selected if one exists.

When a result is activated, the type determines the action:

- desktop app → `app_launcher.launch_application()`
- calculator result → copy its display value to the GTK clipboard
- web result → `web_search.open_web_search()`
- web alias → `web_search.open_web_uri()`

Successful application launches are recorded in history; successful launches
and web opens hide the launcher. Errors are shown in the status label.
Calculator results remain visible and report clipboard success/failure there.

### `desktop_parser.py` — desktop application discovery

`load_desktop_applications()` calls `Gio.AppInfo.get_all()`, keeps
`GioUnix.DesktopAppInfo` objects whose `should_show()` is true, wraps them in
`DesktopApplication`, and sorts by case-insensitive display name.

The wrapper retains the original Gio object, desktop ID, display name,
executable string, description, and `Gio.Icon`. Keeping the original Gio
object matters: launch behavior should use desktop-entry semantics instead of
reconstructing commands from text.

### `fuzzy_search.py` — application matching

`search_applications(applications, query, limit=8)` normalizes whitespace and
case, scores application names and descriptions, sorts by descending score,
and returns up to eight matches.
It accepts optional `history_ids`; a matching desktop ID gets a 40-point
ranking boost. Only successful app launch IDs are recorded by the launcher.

Scoring precedence is exact match, prefix, contiguous substring, then
in-order/non-contiguous character matching. Name scores take precedence over
description scores. This is intentionally a small dependency-free ranker; it
is not Levenshtein distance and can return weak matches for short queries.

### `calculator.py` — safe arithmetic

`calculate(expression)` parses in Python `eval` mode but never evaluates
Python code. It walks the AST and permits numeric constants, unary `+`/`-`,
addition, subtraction, multiplication, division, floor division, modulo, and
bounded integer powers.

Resource limits currently include a 128-character expression, 64 AST nodes,
integer numerator/denominator sizes up to 4096 bits, and exponents from -100
to 100. Results use `Fraction`, so non-terminating decimals remain exact and
display as a fraction (for example `1/3`).

### `web_search.py` — default-browser web search

`build_search_uri(query)` rejects an empty query and URL-encodes the query as
the `q` parameter of a fixed Google HTTPS search URL.
`open_web_search(query)` asks Gio to open that URI with the user's default
browser. `open_web_uri(uri)` opens a validated HTTP(S) URI and rejects other
schemes and credential-bearing URLs. Search text is data in a URL, never shell
syntax.

### `history_manager.py` — recent application history

The module stores up to 20 unique desktop IDs with UTC timestamps in
`$XDG_DATA_HOME/xlauncher/history.json` (default
`~/.local/share/xlauncher/history.json`). A relaunch moves the ID to the top.
Writes use a temporary file and atomic replacement. Missing or malformed data
does not stop the launcher; persistence errors are logged.

### `alias_manager.py` — user aliases

The optional `$XDG_DATA_HOME/xlauncher/aliases.json` file maps one-word,
case-insensitive exact query keys to `app` desktop IDs or `web` HTTP(S) URLs.
Malformed files fall back to normal search; invalid entries are ignored.
Desktop app aliases whose ID is not installed show an error instead of
launching an unrelated command.

### `app_launcher.py` — launch a desktop application

`launch_application(application)` checks that the stored Gio object is a
`GioUnix.DesktopAppInfo`, then calls its `launch([], None)` method. It raises a
clear error if the value is invalid or GLib reports that launch failed.

### `toggle_daemon.py` — per-user command channel

The daemon listens on
`$XDG_RUNTIME_DIR/xlauncher/control.sock`. It verifies ownership and private
permissions on runtime directories, sets restrictive socket permissions, and
limits the Unix socket path length.

If a socket path already exists, startup probes it. A responsive socket means
another daemon is alive and must not be overwritten. A stale owned socket can
be removed and rebound; an unexpected file is refused. Shutdown records the
socket inode identity and removes only its own socket, avoiding deletion of a
replacement socket.

The server accepts `toggle` and `stop`. Its worker thread sends UI callbacks
through `GLib.idle_add()` so GTK operations run on the GTK/GLib main loop.
`control_daemon()` sends a command to an existing daemon or starts one and
waits briefly for its socket. Daemon stdout/stderr are written to
`$XDG_RUNTIME_DIR/xlauncher/daemon.log`.

### `xlauncher-toggle` — executable entrypoint

This Python script finds project modules beside itself when run from the source
tree, or under `$XDG_DATA_HOME/xlauncher` (default
`~/.local/share/xlauncher`) after installation. No arguments mean toggle;
arguments such as `--help` or `--stop` are passed to `main.py`.

### `install.sh` — per-user native install

The shell installer checks the selected Python interpreter and GTK4 import,
then copies application modules, the entrypoint, and SVG icon into user XDG
folders. It writes a wrapper at `~/.local/bin/xlauncher` and a GNOME desktop
entry under the user's applications directory. It does not require `sudo`.

The Python executable can be overridden with `XLAUNCHER_PYTHON`; the binary
directory can be overridden with `XLAUNCHER_BIN_DIR`. The installer is tested
with paths containing spaces.

### `scan_bugs.py` and `tests/`

The scanner uses Python's `ast` module to perform limited structural checks,
then starts unittest discovery in `tests/`. It is a project-specific check,
not a complete static analyzer or security auditor.

Tests cover fuzzy ranking, history persistence and corruption recovery, alias
loading and URL validation, arithmetic success/rejection cases, web URL
encoding, native installation with spaced paths, and socket
stale/live/replacement scenarios.

## Main runtime flows

### Normal application search

1. GTK emits the entry's `changed` signal.
2. `XLauncher._on_search_changed()` first resolves exact aliases; absent an
   alias, it routes calculator and web prefixes or calls `search_applications()`.
3. Matching rows are rebuilt, with app icons rendered from Gio icon objects
   and recent IDs receiving a small score boost.
4. The first result is selected.
5. `Enter` activates the selected desktop entry through Gio.
6. On success, the desktop ID is moved to the top of the JSON history.

### Alias query

1. A trimmed query exactly matching an alias key (case-insensitive) is resolved.
2. App aliases look up the configured desktop ID and use the regular Gio
   launch path; web aliases open a validated HTTP(S) URL through Gio.
3. Missing or invalid alias configuration falls back to normal query handling.

### Calculator query

1. A trimmed query starting with `=` is routed to `calculate()`.
2. A valid expression becomes one `CalculationResult`.
3. Selecting it and pressing `Enter` copies the exact result string to the
   clipboard.
4. Invalid expressions show a status error; they are not sent to app search.

### Web search query

1. A trimmed query starting with `g ` is routed to a `WebSearchResult`.
2. The remaining text is URL-encoded by `urlencode`.
3. Pressing `Enter` opens the fixed Google search URI via Gio.
4. Empty `g ` queries show a status message.

### Toggle daemon

1. GNOME invokes the configured `xlauncher`/`xlauncher-toggle` command.
2. The client connects to the private user socket.
3. It sends `toggle`; if no daemon is running, it starts the daemon and retries.
4. The daemon dispatches the UI toggle onto the GLib main context.

## Setup and developer commands

On Ubuntu, system GTK bindings are expected:

```bash
sudo apt update
sudo apt install python3-gi gir1.2-gtk-4.0
```

Run directly from the project directory:

```bash
/usr/bin/python3 main.py
./xlauncher-toggle
```

Install for the current user:

```bash
./install.sh
/home/baris/.local/bin/xlauncher
```

Run tests and project checks:

```bash
/usr/bin/python3 -m unittest discover -s tests -v
/usr/bin/python3 scan_bugs.py
```

The GNOME custom keyboard shortcut should invoke the installed launcher command
(normally `/home/baris/.local/bin/xlauncher`). GNOME handles the global key;
the Python process does not attempt to capture global keyboard input.

## Visual and platform limitations

- GTK CSS is in `main.py`; the window is borderless with a 600×60 default size.
- Result rows increase the window's natural content height; the results area is
  scrollable and capped.
- SF Pro Display is optional. If it is unavailable, the CSS fallback is
  sans-serif.
- On Wayland, a client cannot guarantee its screen coordinates. `present()` and
  `grab_focus()` request presentation/focus but Mutter may constrain them.
- Do not claim that socket-based toggling itself guarantees focus or placement;
  it only transports a command from GNOME to the launcher process.
- The current source targets GTK4 APIs; do not replace them with GTK3 examples.

## Packaging status

`packaging/` and `scripts/build-appimage.sh` describe an AppImage route, but the
AppImageBuilder tool could not be obtained in the development environment. No
AppImage artifact has been built or tested.

The current recipe is explicitly configured for **Ubuntu Jammy amd64**. Review
its base distribution, Python/GTK versions, GI typelibs, runtime paths, and
application entrypoint before using it as a distribution build. The native
`install.sh` route is the validated installation path; it depends on GTK4 and
PyGObject being installed on the host.

## Coding guidance for future work

1. Read the relevant module and tests before changing code.
2. Confirm bug reports against current source; do not duplicate existing
   behavior.
3. Keep responsibilities separated: UI in `main.py`, desktop discovery in
   `desktop_parser.py`, app ranking in `fuzzy_search.py`, calculations in
   `calculator.py`, web URI/browser behavior in `web_search.py`, process
   control in `toggle_daemon.py`.
4. Keep user text in Turkish and update this brief/README when observable
   behavior or setup changes.
5. Never use `eval()` for calculator input, a shell for desktop-entry `Exec`,
   or a shell to execute web-search text.
6. Preserve explicit errors. Do not silently swallow socket, launch, or
   install failures.
7. Add regression tests for new behavior and run the focused test first.
8. Be precise about what was actually tested; distinguish code/test validation
   from visual desktop testing and package portability.
