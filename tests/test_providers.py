import unittest
from datetime import datetime

from providers import convert_units, date_time_result


class BuiltinProviderTests(unittest.TestCase):
    def test_converts_units_with_decimal_accuracy(self) -> None:
        self.assertEqual(convert_units("100 cm to m").value, "1")
        self.assertEqual(convert_units("20 c to f").value, "68")
        self.assertEqual(
            convert_units("25 km to mile").value,
            "15.53427980593334924043585461",
        )

    def test_reports_unsupported_and_incompatible_units(self) -> None:
        self.assertEqual(convert_units("5 foo to bar").kind, "error")
        self.assertEqual(convert_units("5 km to kg").kind, "error")

    def test_date_time_commands_use_injected_local_datetime(self) -> None:
        moment = datetime(2026, 11, 8, 13, 30, 0)
        self.assertEqual(date_time_result("time", moment).title, "13:30:00")
        self.assertEqual(date_time_result("today", moment).title, "08.11.2026")
        self.assertEqual(
            date_time_result("date", moment).title,
            "Pazar, 08 Kasım 2026",
        )
        self.assertIsNone(date_time_result("tomorrow", moment))


if __name__ == "__main__":
    unittest.main()
