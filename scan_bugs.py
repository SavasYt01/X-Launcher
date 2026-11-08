#!/usr/bin/env python3
"""Run focused structural and runtime checks for the X-Launcher project."""

import ast
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REQUIRED_FILES = (
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
    "xlauncher-toggle",
    "install.sh",
    "uninstall.sh",
    ".github/workflows/tests.yml",
    ".github/workflows/appimage.yml",
    "packaging/xlauncher.desktop",
    "packaging/xlauncher.svg",
    "packaging/AppRun",
    "packaging/appimage-env.sh",
    "packaging/THIRD_PARTY_NOTICES.md",
    "scripts/build_appdir.py",
    "scripts/build-appimage.sh",
    "scripts/test-appimage.sh",
    "themes/default-dark/theme.css",
)


class Scan:
    def __init__(self) -> None:
        self.failures = 0

    def check(self, description: str, condition: bool, detail: str = "") -> None:
        state = "OK" if condition else "FAIL"
        suffix = f" — {detail}" if detail else ""
        print(f"[{state}] {description}{suffix}")
        if not condition:
            self.failures += 1


def parse_module(scan: Scan, relative_path: str) -> ast.Module | None:
    path = ROOT / relative_path
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError, UnicodeError) as error:
        scan.check(f"Python syntax: {relative_path}", False, str(error))
        return None


def call_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Name):
            names.add(function.id)
        elif isinstance(function, ast.Attribute):
            names.add(function.attr)
    return names


def main() -> int:
    scan = Scan()
    print("X-Launcher diagnostic scan\n")

    missing = [name for name in REQUIRED_FILES if not (ROOT / name).is_file()]
    scan.check(
        "Required project files",
        not missing,
        ", ".join(missing) if missing else f"{len(REQUIRED_FILES)} files found",
    )

    modules = (
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
        "scripts/build_appdir.py",
    )
    trees = {name: parse_module(scan, name) for name in modules}
    syntactically_valid = all(tree is not None for tree in trees.values())
    scan.check("Python module syntax", syntactically_valid)

    parser_tree = trees["desktop_parser.py"]
    if parser_tree is not None:
        parser_calls = call_names(parser_tree)
        scan.check(
            "Hidden desktop entries are filtered",
            "should_show" in parser_calls,
            "Gio's should_show() applies NoDisplay/visibility rules",
        )

    main_tree = trees["main.py"]
    if main_tree is not None:
        main_calls = call_names(main_tree)
        scan.check(
            "Window presentation and focus",
            "present" in main_calls and "grab_focus" in main_calls,
        )
        scan.check(
            "GTK4 CSS provider is registered",
            "add_provider_for_display" in main_calls,
        )
        scan.check(
            "Dynamic GTK4 theme is loaded",
            "load_theme" in main_calls and "load_from_string" in main_calls,
        )
        scan.check(
            "Calculator results can be copied to the clipboard",
            "set_text" in main_calls and "get_clipboard" in main_calls,
        )

    calculator_tree = trees["calculator.py"]
    if calculator_tree is not None:
        calculator_source = (ROOT / "calculator.py").read_text(encoding="utf-8")
        scan.check(
            "Calculator avoids dynamic evaluation",
            "eval(" not in calculator_source and "ast.parse" in calculator_source,
        )
        scan.check(
            "Calculator bounds expression complexity",
            "MAX_EXPRESSION_LENGTH" in calculator_source
            and "MAX_AST_NODES" in calculator_source
            and "MAX_INTEGER_BITS" in calculator_source,
        )

    web_search_tree = trees["web_search.py"]
    if web_search_tree is not None:
        web_search_source = (ROOT / "web_search.py").read_text(encoding="utf-8")
        scan.check(
            "Web search query is URL-encoded",
            "urlencode" in web_search_source and "launch_default_for_uri" in call_names(web_search_tree),
        )

    daemon_tree = trees["toggle_daemon.py"]
    if daemon_tree is not None:
        daemon_source = (ROOT / "toggle_daemon.py").read_text(encoding="utf-8")
        scan.check(
            "Per-user socket directory is validated",
            "XDG_RUNTIME_DIR" in daemon_source and "os.getuid()" in daemon_source,
        )
        scan.check(
            "Stale socket is probed before removal",
            "probe.connect" in daemon_source and "self.path.unlink()" in daemon_source,
        )

    app_tree = trees["app_launcher.py"]
    if app_tree is not None:
        app_calls = call_names(app_tree)
        scan.check(
            "Desktop entries launch through GLib",
            "launch" in app_calls,
        )
        unsafe_shell_launch = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"Popen", "run", "call"}
            and any(
                keyword.arg == "shell"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in node.keywords
            )
            for node in ast.walk(app_tree)
        )
        scan.check("No shell-based application launch", not unsafe_shell_launch)
    launch_context_tree = trees["app_launch_context.py"]
    if launch_context_tree is not None:
        context_calls = call_names(launch_context_tree)
        scan.check(
            "AppImage child applications restore host environment",
            "AppLaunchContext" in context_calls and "unsetenv" in context_calls,
        )

    cli_tree = trees["launcher_cli.py"]
    if cli_tree is not None:
        cli_source = (ROOT / "launcher_cli.py").read_text(encoding="utf-8")
        scan.check(
            "CLI help and doctor dispatch before GTK imports",
            "from doctor import run" in cli_source and "import gi" not in cli_source,
        )

    appimage_sources = (
        (ROOT / "packaging" / "AppRun").read_text(encoding="utf-8")
        + (ROOT / "scripts" / "build-appimage.sh").read_text(encoding="utf-8")
        + (ROOT / "scripts" / "test-appimage.sh").read_text(encoding="utf-8")
    )
    scan.check(
        "AppImage tool is checksum-pinned and smoke-tested",
        "APPIMAGETOOL_SHA256=" in appimage_sources
        and "--appimage-extract" in appimage_sources
        and "--doctor" in appimage_sources,
    )

    print("\nRunning unit tests:")
    test_result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=False,
    )
    scan.check("Unit test suite", test_result.returncode == 0)
    print(f"\nScan complete: {scan.failures} failure(s).")
    return 1 if scan.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
