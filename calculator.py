"""Safely evaluate small arithmetic expressions for the launcher."""

import ast
from dataclasses import dataclass
from fractions import Fraction


MAX_EXPRESSION_LENGTH = 128
MAX_AST_NODES = 64
MAX_INTEGER_BITS = 4096
MAX_EXPONENT = 100


class CalculationError(ValueError):
    """Raised when an expression is invalid or outside the calculator limits."""


@dataclass(frozen=True)
class CalculationResult:
    expression: str
    value: Fraction

    @property
    def display_value(self) -> str:
        if self.value.denominator == 1:
            return str(self.value.numerator)
        return f"{self.value.numerator}/{self.value.denominator}"


def _check_size(value: Fraction) -> Fraction:
    if (
        abs(value.numerator).bit_length() > MAX_INTEGER_BITS
        or value.denominator.bit_length() > MAX_INTEGER_BITS
    ):
        raise CalculationError("Sonuç izin verilen büyüklüğü aşıyor.")
    return value


def _evaluate_node(node: ast.AST) -> Fraction:
    if isinstance(node, ast.Constant) and not isinstance(node.value, bool):
        if isinstance(node.value, (int, float)):
            try:
                return _check_size(Fraction(str(node.value)))
            except (ValueError, ZeroDivisionError) as error:
                raise CalculationError("Geçersiz sayı.") from error
        raise CalculationError("Yalnızca sayılar kullanılabilir.")

    if isinstance(node, ast.UnaryOp):
        operand = _evaluate_node(node.operand)
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, ast.USub):
            return -operand
        raise CalculationError("Bu tekli işlem desteklenmiyor.")

    if not isinstance(node, ast.BinOp):
        raise CalculationError("Yalnızca temel aritmetik işlemler kullanılabilir.")

    left = _evaluate_node(node.left)
    right = _evaluate_node(node.right)
    try:
        if isinstance(node.op, ast.Add):
            result = left + right
        elif isinstance(node.op, ast.Sub):
            result = left - right
        elif isinstance(node.op, ast.Mult):
            result = left * right
        elif isinstance(node.op, ast.Div):
            result = left / right
        elif isinstance(node.op, ast.FloorDiv):
            result = Fraction(left // right)
        elif isinstance(node.op, ast.Mod):
            result = left % right
        elif isinstance(node.op, ast.Pow):
            if right.denominator != 1 or abs(right.numerator) > MAX_EXPONENT:
                raise CalculationError("Üs, -100 ile 100 arasında bir tam sayı olmalı.")
            if left == 0 and right < 0:
                raise CalculationError("Sıfırın negatif kuvveti tanımsızdır.")
            result = left**right.numerator
        else:
            raise CalculationError("Bu aritmetik işlem desteklenmiyor.")
    except CalculationError:
        raise
    except ZeroDivisionError as error:
        raise CalculationError("Sıfıra bölme yapılamaz.") from error
    except (OverflowError, ValueError) as error:
        raise CalculationError("İşlem hesaplanamadı.") from error
    return _check_size(result)


def calculate(expression: str) -> CalculationResult:
    """Evaluate an arithmetic expression without executing arbitrary Python."""
    expression = expression.strip()
    if not expression:
        raise CalculationError("Hesaplanacak bir ifade yaz.")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise CalculationError("İfade çok uzun.")

    try:
        tree = ast.parse(expression, mode="eval")
    except (SyntaxError, ValueError) as error:
        raise CalculationError("İfade tamamlanmamış veya geçersiz.") from error

    if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
        raise CalculationError("İfade çok karmaşık.")

    value = _evaluate_node(tree.body)
    return CalculationResult(expression=expression, value=value)
