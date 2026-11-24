"""Низкоуровневые проверки атрибутов.

Содержит правила для имён полей (нелатинские символы), разбора дат,
кодировок (кракозябры), пробелов по краям и внутри значений,
управляющих и невидимых символов и числовых значений в текстовых полях.
"""

from __future__ import annotations

import unicodedata
from typing import List, Optional, Tuple

CONTROL_CHARACTER_NAMES = {
    "\t": "TAB",
    "\n": "LF",
    "\r": "CR",
    "\v": "VT",
    "\f": "FF",
    "\x00": "NUL",
    "\x1b": "ESC",
    "\u00a0": "NBSP",
    "\u00ad": "SHY",
    "\u200b": "ZWSP",
    "\u200c": "ZWNJ",
    "\u200d": "ZWJ",
    "\u2028": "LS",
    "\u2029": "PS",
    "\u202f": "NNBSP",
    "\u2060": "WJ",
    "\ufeff": "BOM",
}

_CONTROL_ESCAPES = {
    "\t": "\\t",
    "\n": "\\n",
    "\r": "\\r",
    "\v": "\\v",
    "\f": "\\f",
    "\x00": "\\0",
}

_INVISIBLE_CATEGORIES = frozenset({"Cc", "Cf", "Zl", "Zp", "Zs"})



_EDGE_ESCAPES = {
    " ": "·",
    "\t": "\\t",
    "\n": "\\n",
    "\r": "\\r",
    "\v": "\\v",
    "\f": "\\f",
}






MIN_DATE_YEAR = 1900

_DATE_SEPARATORS = ("-", ".", "/")


def _valid_date(year: int, month: int, day: int) -> bool:
    if not (1 <= month <= 12):
        return False
    if not (1 <= day <= 31):
        return False
    days_in_month = (
        31,
        29 if _is_leap_year(year) else 28,
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    )
    return day <= days_in_month[month - 1]


def _is_leap_year(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def parse_date_text(value: str) -> Optional[Tuple[int, int, int]]:
    """Разобрать дату из строки: год, месяц, день или None.

    Поддерживаются записи вида ГГГГ-ММ-ДД, ДД.ММ.ГГГГ, ДД/ММ/ГГГГ и
    ГГГГ/ММ/ДД, в том числе с временем через «T» или пробел. Значения,
    которые не разбираются как дата, возвращают None.
    """

    text = value.strip()
    if not text:
        return None

    for marker in ("T", " "):
        if marker in text:
            head, _, tail = text.partition(marker)
            if head and tail:
                text = head
            break

    separator = ""
    for candidate in _DATE_SEPARATORS:
        if candidate in text:
            separator = candidate
            break
    if not separator:
        return None

    parts = text.split(separator)
    if len(parts) != 3:
        return None
    if not all(part.isdigit() for part in parts):
        return None

    first, second, third = (int(part) for part in parts)
    if len(parts[0]) == 4:
        year, month, day = first, second, third
    elif len(parts[2]) == 4:
        day, month, year = first, second, third
    else:
        return None

    if year == 0:
        return 0, month, day
    if not _valid_date(year, month, day):
        return None
    return year, month, day


def date_year_out_of_range(
    value: str,
    *,
    min_year: int = MIN_DATE_YEAR,
    max_year: int = 0,
) -> Optional[int]:
    """Вернуть год даты, если он вне разумного диапазона."""

    parsed = parse_date_text(value)
    if parsed is None:
        return None
    year = parsed[0]
    if year < min_year:
        return year
    if max_year and year > max_year:
        return year
    return None


DECIMAL_SEPARATORS = (".", ",")


def numeric_text_kind(value: str) -> str:
    """Вернуть вид числа в текстовом значении: integer, real или пусто.

    Значение считается числом, только если состоит из цифр, одного
    десятичного разделителя, знака и экспоненты и не содержит пробелов
    внутри. Строки с ведущими нулями (коды, идентификаторы) остаются
    числами: «007» — это число, записанное как текст.
    """

    text = value.strip()
    if not text:
        return ""

    if text[0] in "+-":
        text = text[1:]
    if not text:
        return ""

    exponent = ""
    for marker in ("e", "E"):
        if marker in text:
            text, _, exponent_part = text.partition(marker)
            exponent = exponent_part
            break
    if exponent:
        exponent = exponent[1:] if exponent[0] in "+-" else exponent
        if not exponent.isdigit():
            return ""

    separators = sum(text.count(item) for item in DECIMAL_SEPARATORS)
    if separators > 1:
        return ""
    digits = "".join(
        character for character in text if not character.isdigit()
    )
    if digits and digits not in DECIMAL_SEPARATORS:
        return ""
    if not any(character.isdigit() for character in text):
        return ""

    if separators:
        return "real"
    if exponent:
        return "real"
    return "integer"


def looks_numeric_text(value: str) -> bool:
    """Вернуть True, если текстовое значение записано числом."""

    return bool(numeric_text_kind(value))



MOJIBAKE_SOURCE_ENCODINGS = ("latin-1", "cp1252", "cp1251")
MOJIBAKE_MARKERS = "ÐÑÃÂ"
MOJIBAKE_SEQUENCES = ("â€", "ï»¿", "ÐŸ", "Ð¾", "Ð¡")


def repair_mojibake(value: str, limit: int = 80) -> str:
    """Вернуть исправленный текст, если значение похоже на кракозябры.

    Кракозябры появляются, когда UTF-8 читают как однобайтовую
    кодировку: «ÐœÐ¾ÑÐºÐ²Ð°» вместо «Москва». Значение пытаются
    закодировать обратно в однобайтовую кодировку и снова прочитать
    как UTF-8; если получается другой осмысленный не-ASCII текст,
    возвращается он. Иначе возвращается пустая строка.
    """

    text = (value or "").strip()
    if len(text) < 2 or text.isascii():
        return ""

    for source in MOJIBAKE_SOURCE_ENCODINGS:
        try:
            raw = text.encode(source)
        except (UnicodeEncodeError, LookupError):
            continue
        try:
            decoded = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if decoded == text or not decoded.strip() or decoded.isascii():
            continue
        return decoded[:limit]
    return ""


def mojibake_markers(value: str) -> int:
    """Оценить, сколько в значении признаков неверной кодировки."""

    text = value or ""
    score = sum(text.count(marker) for marker in MOJIBAKE_MARKERS)
    for sequence in MOJIBAKE_SEQUENCES:
        score += 2 * text.count(sequence)
    return score


def looks_like_mojibake(value: str) -> bool:
    """Вернуть True, если значение похоже на текст в неверной кодировке."""

    if not value or len(value.strip()) < 2 or value.isascii():
        return False
    if repair_mojibake(value):
        return True
    return mojibake_markers(value) >= 2


def escape_mojibake(value: str, limit: int = 60) -> str:
    """Обрезать значение для отчёта."""

    text = (value or "").strip()
    if len(text) > limit:
        return text[:limit] + "…"
    return text


INNER_SPACE_RUN = 2


def inner_space_runs(value: str) -> Tuple[int, ...]:
    """Вернуть длины последовательностей пробелов внутри значения."""

    stripped = value.strip()
    if not stripped:
        return ()

    runs: List[int] = []
    current = 0
    for character in stripped:
        if character.isspace():
            current += 1
            continue
        if current >= INNER_SPACE_RUN:
            runs.append(current)
        current = 0
    return tuple(runs)


def has_inner_spaces(value: str) -> bool:
    """Вернуть True, если внутри значения два и более пробела подряд."""

    return bool(inner_space_runs(value))


def escape_inner_spaces(value: str, limit: int = 60) -> str:
    """Показать пробелы внутри значения видимыми символами."""

    text = "«{}»".format(
        "".join(
            _EDGE_ESCAPES.get(character, character) for character in value
        )
    )
    if len(text) > limit:
        return text[:limit] + "…"
    return text

def edge_whitespace(value: str) -> Tuple[str, str]:
    """Вернуть ведущие и замыкающие пробельные символы значения."""

    stripped = value.strip()
    if not stripped:
        return value, ""
    start = value.index(stripped)
    end = start + len(stripped)
    return value[:start], value[end:]


def escape_edge_whitespace(value: str, limit: int = 60) -> str:
    """Показать пробелы по краям значения видимыми символами."""

    leading, trailing = edge_whitespace(value)

    def escape(part: str) -> str:
        return "".join(
            _EDGE_ESCAPES.get(character, "\\u{:04x}".format(ord(character)))
            for character in part
        )

    text = "{}«{}»{}".format(escape(leading), value.strip(), escape(trailing))
    if len(text) > limit:
        return text[:limit] + "…"
    return text

def is_control_or_invisible(character: str) -> bool:
    """Вернуть True для управляющих и невидимых символов.

    Управляющие символы C0 и C1, форматирующие символы (Cf), разделители
    строк и абзацев, а также неразрывные и нулевой ширины пробелы.
    Обычный пробел, буквы и цифры проблемными не считаются.
    """

    if not character:
        return False
    code = ord(character)
    if code < 32 or code == 127:
        return True
    if 0x80 <= code <= 0x9F:
        return True
    if character == " ":
        return False
    return unicodedata.category(character) in _INVISIBLE_CATEGORIES


def control_characters(value: str) -> Tuple[str, ...]:
    """Вернуть найденные управляющие и невидимые символы без повторов."""

    found: list = []
    for character in value:
        if is_control_or_invisible(character) and character not in found:
            found.append(character)
    return tuple(found)


def control_character_label(character: str) -> str:
    """Название символа для отчёта: «TAB (U+0009)» или «U+2007»."""

    code = ord(character)
    name = CONTROL_CHARACTER_NAMES.get(character)
    if name:
        return "{} (U+{:04X})".format(name, code)
    return "U+{:04X}".format(code)


def escape_control_characters(value: str, limit: int = 80) -> str:
    """Показать управляющие символы в виде \\t, \\n и \\uXXXX."""

    parts: list = []
    for character in value:
        escape = _CONTROL_ESCAPES.get(character)
        if escape is not None:
            parts.append(escape)
        elif is_control_or_invisible(character):
            parts.append("\\u{:04x}".format(ord(character)))
        else:
            parts.append(character)
    text = "".join(parts)
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def has_non_latin_characters(value: str) -> bool:
    """Вернуть True, если в строке есть символы вне ASCII.

    Кириллица, греческие буквы, иероглифы и другие не-ASCII символы
    считаются проблемными для имён полей. Цифры, подчёркивания, пробелы
    и обычная латиница допускаются.
    """

    return any(ord(character) > 127 for character in value)
