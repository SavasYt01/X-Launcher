import unittest

from alias_manager import Alias
from command_router import route_query


class CommandRouterTests(unittest.TestCase):
    def test_exact_alias_precedes_prefix_and_command_routes(self) -> None:
        alias = Alias(key="yt", kind="web", value="https://youtube.com")
        self.assertEqual(route_query("yt", alias).kind, "alias")
        route = route_query("yt python tutorial")
        self.assertEqual(route.kind, "web_search")
        self.assertEqual(route.value, ("python tutorial", "youtube"))

    def test_routes_existing_and_new_commands(self) -> None:
        self.assertEqual(route_query("= 2 + 2").kind, "calculator")
        self.assertEqual(route_query("g python").value, ("python", "google"))
        self.assertEqual(route_query("s GTK", default_engine="brave").value, ("GTK", "brave"))
        self.assertEqual(route_query("S GTK", default_engine="brave").value, ("GTK", "brave"))
        self.assertEqual(route_query("cb clear").value, "clear")
        self.assertEqual(route_query("25 km to mile").kind, "provider")
        self.assertEqual(route_query("today").kind, "provider")
        self.assertEqual(route_query("firefox").kind, "applications")


if __name__ == "__main__":
    unittest.main()
