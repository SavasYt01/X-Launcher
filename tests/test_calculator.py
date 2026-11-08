import unittest
from fractions import Fraction

from calculator import CalculationError, calculate


class CalculatorTests(unittest.TestCase):
    def test_calculates_parenthesized_arithmetic(self) -> None:
        result = calculate("(2 + 3) * 4")
        self.assertEqual(result.value, Fraction(20))
        self.assertEqual(result.display_value, "20")

    def test_keeps_non_terminating_results_exact(self) -> None:
        result = calculate("1 / 3")
        self.assertEqual(result.value, Fraction(1, 3))
        self.assertEqual(result.display_value, "1/3")

    def test_supports_unary_and_integer_powers(self) -> None:
        self.assertEqual(calculate("-2 ** 3").display_value, "-8")
        self.assertEqual(calculate("2 ** -2").display_value, "1/4")

    def test_rejects_division_by_zero(self) -> None:
        with self.assertRaisesRegex(CalculationError, "Sıfıra bölme"):
            calculate("5 / 0")

    def test_rejects_arbitrary_python_expressions(self) -> None:
        for expression in ("__import__('os')", "open('/tmp/file')", "2 ^ 3"):
            with self.subTest(expression=expression):
                with self.assertRaises(CalculationError):
                    calculate(expression)

    def test_rejects_excessive_expression_and_power(self) -> None:
        with self.assertRaisesRegex(CalculationError, "çok uzun"):
            calculate("1" * 129)
        with self.assertRaisesRegex(CalculationError, "Üs"):
            calculate("2 ** 101")


if __name__ == "__main__":
    unittest.main()
