"""Per-user Unix socket control for the GTK launcher."""

import errno
import os
import socket
import stat
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Callable

from gi.repository import GLib


def _runtime_directory() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if not runtime:
        raise RuntimeError("XDG_RUNTIME_DIR is not set; a user session runtime directory is required.")

    runtime_path = Path(runtime)
    try:
        info = runtime_path.stat()
    except OSError as error:
        raise RuntimeError(f"Cannot access XDG_RUNTIME_DIR ({runtime_path}): {error}") from error
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise RuntimeError(f"XDG_RUNTIME_DIR is not a directory owned by this user: {runtime_path}")

    control_directory = runtime_path / "xlauncher"
    try:
        control_directory.mkdir(mode=0o700, exist_ok=True)
        info = control_directory.stat()
    except OSError as error:
        raise RuntimeError(f"Cannot prepare launcher runtime directory: {error}") from error
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise RuntimeError(f"Launcher runtime directory must be private and user-owned: {control_directory}")
    return control_directory


def _socket_path() -> Path:
    path = _runtime_directory() / "control.sock"
    if len(os.fsencode(path)) >= 104:
        raise RuntimeError(f"Unix socket path is too long: {path}")
    return path


class ToggleServer:
    def __init__(self, handler: Callable[[str], None]) -> None:
        self.path = _socket_path()
        self.handler = handler
        self._stop_event = threading.Event()
        self._socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._socket_identity: tuple[int, int] | None = None

    def start(self) -> None:
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            try:
                server.bind(str(self.path))
            except OSError as error:
                if error.errno != errno.EADDRINUSE:
                    raise
                probe = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    probe.settimeout(0.25)
                    probe.connect(str(self.path))
                except ConnectionRefusedError:
                    info = self.path.lstat()
                    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid():
                        raise RuntimeError(f"Refusing to remove an unexpected file: {self.path}") from error
                    self.path.unlink()
                    server.bind(str(self.path))
                except FileNotFoundError:
                    server.bind(str(self.path))
                else:
                    raise RuntimeError(f"Another launcher daemon is already using {self.path}") from error
                finally:
                    probe.close()
            os.chmod(self.path, 0o600)
            server.listen(8)
            server.settimeout(0.5)
        except OSError as error:
            server.close()
            raise RuntimeError(f"Cannot create launcher control socket {self.path}: {error}") from error
        except RuntimeError:
            server.close()
            raise

        self._socket = server
        info = self.path.stat()
        self._socket_identity = (info.st_dev, info.st_ino)
        self._thread = threading.Thread(target=self._serve, name="xlauncher-control", daemon=True)
        self._thread.start()

    def _serve(self) -> None:
        assert self._socket is not None
        while not self._stop_event.is_set():
            try:
                connection, _ = self._socket.accept()
            except socket.timeout:
                continue
            except OSError as error:
                if self._stop_event.is_set():
                    break
                print(f"X-Launcher control socket stopped unexpectedly: {error}", file=sys.stderr)
                break

            if self._stop_event.is_set():
                connection.close()
                break

            with connection:
                connection.settimeout(2)
                try:
                    request = connection.recv(128).decode("utf-8").strip()
                    if not request:
                        continue
                    if request not in {"toggle", "stop"}:
                        connection.sendall(b"ERROR unknown command\n")
                        continue
                    GLib.idle_add(self.handler, request)
                    connection.sendall(b"OK\n")
                except UnicodeDecodeError as error:
                    print(f"X-Launcher received an invalid control message: {error}", file=sys.stderr)
                except OSError as error:
                    print(f"X-Launcher control client disconnected with an error: {error}", file=sys.stderr)
                    continue

    def stop(self) -> None:
        self._stop_event.set()
        if self._socket is not None and self._thread is not None:
            try:
                info = self.path.lstat()
            except FileNotFoundError:
                info = None
            if info is not None and self._socket_identity == (info.st_dev, info.st_ino):
                wakeup = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                try:
                    wakeup.settimeout(0.25)
                    wakeup.connect(str(self.path))
                except (ConnectionRefusedError, FileNotFoundError):
                    pass
                except OSError as error:
                    print(f"X-Launcher could not wake its control listener: {error}", file=sys.stderr)
                finally:
                    wakeup.close()
        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        try:
            info = self.path.lstat()
        except FileNotFoundError:
            return
        if self._socket_identity == (info.st_dev, info.st_ino) and stat.S_ISSOCK(info.st_mode):
            self.path.unlink()
        self._socket_identity = None


def _send_command(command: str, timeout: float = 2.0) -> bool:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        client.connect(str(_socket_path()))
        client.sendall(f"{command}\n".encode("utf-8"))
        response = client.recv(128).decode("utf-8").strip()
    except (ConnectionRefusedError, FileNotFoundError):
        return False
    except OSError as error:
        raise RuntimeError(f"Cannot communicate with the launcher daemon: {error}") from error
    finally:
        client.close()
    if response != "OK":
        raise RuntimeError(f"Launcher daemon rejected the command: {response}")
    return True


def control_daemon(command: str, script_path: Path) -> int:
    try:
        if command == "stop":
            if not _send_command("stop"):
                print("X-Launcher daemon is not running.", file=sys.stderr)
                return 1
            deadline = time.monotonic() + 3
            socket_path = _socket_path()
            while socket_path.exists() and time.monotonic() < deadline:
                time.sleep(0.05)
            if socket_path.exists():
                raise RuntimeError("The launcher daemon did not stop within 3 seconds.")
            return 0

        if _send_command("toggle"):
            return 0

        runtime = _runtime_directory()
        log_path = runtime / "daemon.log"
        log_file = log_path.open("a", encoding="utf-8")
        try:
            appimage = os.environ.get("APPIMAGE")
            command = (
                [appimage, "--daemon"]
                if appimage
                else [sys.executable, str(script_path), "--daemon"]
            )
            subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                close_fds=True,
            )
        finally:
            log_file.close()

        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if _send_command("toggle", timeout=0.25):
                return 0
            time.sleep(0.05)
        raise RuntimeError(f"Launcher daemon did not start. Check its log: {log_path}")
    except (OSError, RuntimeError) as error:
        print(f"X-Launcher: {error}", file=sys.stderr)
        return 1
