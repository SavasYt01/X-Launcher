import os
import socket
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from toggle_daemon import ToggleServer
except ImportError:
    ToggleServer = None


@unittest.skipIf(ToggleServer is None, "PyGObject is required for socket daemon tests")
class ToggleServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.runtime_directory = Path(self.temporary_directory.name)
        self.runtime_directory.chmod(0o700)
        self.environment = patch.dict(
            os.environ,
            {"XDG_RUNTIME_DIR": str(self.runtime_directory)},
        )
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.addCleanup(self.temporary_directory.cleanup)

    def test_removes_a_stale_socket_before_binding(self) -> None:
        control_directory = self.runtime_directory / "xlauncher"
        control_directory.mkdir(mode=0o700)
        socket_path = control_directory / "control.sock"
        stale_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale_socket.bind(str(socket_path))
        stale_socket.close()

        server = ToggleServer(lambda command: self.assertIn(command, {"toggle", "stop"}))
        server.start()
        self.addCleanup(server.stop)
        self.assertTrue(socket_path.exists())

    def test_refuses_to_replace_a_live_daemon_socket(self) -> None:
        first_server = ToggleServer(lambda command: self.assertIn(command, {"toggle", "stop"}))
        first_server.start()
        self.addCleanup(first_server.stop)

        second_server = ToggleServer(lambda command: self.assertIn(command, {"toggle", "stop"}))
        with self.assertRaisesRegex(RuntimeError, "already using"):
            second_server.start()

    def test_does_not_remove_a_replacement_socket_during_shutdown(self) -> None:
        server = ToggleServer(lambda command: self.assertIn(command, {"toggle", "stop"}))
        server.start()
        socket_path = server.path
        socket_path.unlink()

        replacement = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        replacement.bind(str(socket_path))
        replacement.listen()
        server.stop()
        try:
            self.assertTrue(socket_path.exists())
        finally:
            replacement.close()
            socket_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
