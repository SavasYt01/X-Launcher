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

    def test_routes_web_search_prefixes_case_insensitively(self) -> None:
        expected = {
            "g python": ("python", "google"),
            "ddg gtk": ("gtk", "duckduckgo"),
            "br linux": ("linux", "brave"),
            "yt müzik": ("müzik", "youtube"),
            "gh xlauncher": ("xlauncher", "github"),
            "s bir şey": ("bir şey", "google"),
        }
        for query, value in expected.items():
            with self.subTest(query=query):
                self.assertEqual(route_query(query).kind, "web_search")
                self.assertEqual(route_query(query).value, value)
        self.assertEqual(route_query("DDG GTK").value, ("GTK", "duckduckgo"))

    def test_routes_existing_and_new_commands(self) -> None:
        self.assertEqual(route_query("help").kind, "help")
        self.assertEqual(route_query("HELP").kind, "help")
        self.assertEqual(route_query("= 2 + 2").kind, "calculator")
        self.assertEqual(route_query("5*3").kind, "calculator")
        self.assertEqual(route_query("(10+2)/3").kind, "calculator")
        self.assertEqual(route_query("12.5 + 7").kind, "calculator")
        self.assertEqual(route_query("2").kind, "applications")
        self.assertEqual(route_query("g python").value, ("python", "google"))
        self.assertEqual(route_query("s GTK", default_engine="brave").value, ("GTK", "brave"))
        self.assertEqual(route_query("S GTK", default_engine="brave").value, ("GTK", "brave"))
        self.assertEqual(route_query("cb clear").value, "clear")
        self.assertEqual(route_query("CB").value, "list")
        self.assertEqual(route_query("F fotoğraf.png").value, "fotoğraf.png")
        self.assertEqual(route_query("file indirilenler").value, "indirilenler")
        self.assertEqual(route_query("25 km to mile").kind, "provider")
        self.assertEqual(route_query("today").kind, "provider")
        self.assertEqual(route_query("firefox").kind, "applications")


if __name__ == "__main__":
    unittest.main()
