"""Small built-in non-network command providers."""

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class ProviderResult:
    kind: str
    title: str
    description: str
    value: str


_UNIT_FACTORS = {
    "km": ("length", Decimal("1000")),
    "m": ("length", Decimal("1")),
    "cm": ("length", Decimal("0.01")),
    "mm": ("length", Decimal("0.001")),
    "mile": ("length", Decimal("1609.344")),
    "mi": ("length", Decimal("1609.344")),
    "ft": ("length", Decimal("0.3048")),
    "kg": ("mass", Decimal("1")),
    "g": ("mass", Decimal("0.001")),
    "lb": ("mass", Decimal("0.45359237")),
    "c": ("temperature", Decimal("1")),
    "°c": ("temperature", Decimal("1")),
    "f": ("temperature", Decimal("1")),
    "°f": ("temperature", Decimal("1")),
}
_UNIT_PATTERN = re.compile(
    r"^\s*([-+]?\d+(?:[.,]\d+)?)\s+([a-zA-Z°]+)\s+(?:to|in)\s+([a-zA-Z°]+)\s*$",
    re.IGNORECASE,
)
_TURKISH_WEEKDAYS = (
    "Pazartesi",
    "Salı",
    "Çarşamba",
    "Perşembe",
    "Cuma",
    "Cumartesi",
    "Pazar",
)
_TURKISH_MONTHS = (
    "Ocak",
    "Şubat",
    "Mart",
    "Nisan",
    "Mayıs",
    "Haziran",
    "Temmuz",
    "Ağustos",
    "Eylül",
    "Ekim",
    "Kasım",
    "Aralık",
)


def _format_decimal(value: Decimal) -> str:
    normalized = value.normalize()
    if normalized == normalized.to_integral():
        return str(normalized.quantize(Decimal(1)))
    return format(normalized, "f")


def convert_units(query: str) -> ProviderResult | None:
    if not re.search(r"\b(?:to|in)\b", query, re.IGNORECASE):
        return None
    match = _UNIT_PATTERN.match(query)
    if match is None:
        return ProviderResult("error", "Birim dönüştürücü", "Biçim: 25 km to mile", "")
    amount_text, source_text, target_text = match.groups()
    source = source_text.casefold()
    target = target_text.casefold()
    if source not in _UNIT_FACTORS or target not in _UNIT_FACTORS:
        return ProviderResult(
            "error",
            "Desteklenmeyen birim",
            f"{source_text} veya {target_text} birimi desteklenmiyor.",
            "",
        )
    source_type, source_factor = _UNIT_FACTORS[source]
    target_type, target_factor = _UNIT_FACTORS[target]
    if source_type != target_type:
        return ProviderResult(
            "error", "Birim uyuşmazlığı", "Bu birimler birbirine dönüştürülemez.", ""
        )
    try:
        amount = Decimal(amount_text.replace(",", "."))
        if source_type == "temperature":
            if source in {"f", "°f"}:
                celsius = (amount - Decimal(32)) * Decimal(5) / Decimal(9)
            else:
                celsius = amount
            result = (
                celsius * Decimal(9) / Decimal(5) + Decimal(32)
                if target in {"f", "°f"}
                else celsius
            )
        else:
            result = amount * source_factor / target_factor
    except InvalidOperation:
        return ProviderResult("error", "Geçersiz sayı", "Sayı dönüştürülemedi.", "")
    text = f"{_format_decimal(amount)} {source_text} = {_format_decimal(result)} {target_text}"
    return ProviderResult("unit", text, "Dönüştürme sonucu", _format_decimal(result))


def date_time_result(query: str, now: datetime | None = None) -> ProviderResult | None:
    command = query.strip().casefold()
    current = now or datetime.now().astimezone()
    if command == "time":
        return ProviderResult(
            "datetime", current.strftime("%H:%M:%S"), "Yerel saat", current.isoformat()
        )
    if command == "today":
        return ProviderResult(
            "datetime", current.strftime("%d.%m.%Y"), "Bugünün tarihi", current.date().isoformat()
        )
    if command == "date":
        return ProviderResult(
            "datetime",
            f"{_TURKISH_WEEKDAYS[current.weekday()]}, "
            f"{current.day:02d} {_TURKISH_MONTHS[current.month - 1]} {current.year}",
            "Yerel tarih",
            current.date().isoformat(),
        )
    return None
