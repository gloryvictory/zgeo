"""Проверка имён атрибутивных полей на нелатинские символы."""

from __future__ import annotations


def has_non_latin_characters(value: str) -> bool:
    """Вернуть True, если в строке есть символы вне ASCII.

    Кириллица, греческие буквы, иероглифы и другие не-ASCII символы
    считаются проблемными для имён полей. Цифры, подчёркивания, пробелы
    и обычная латиница допускаются.
    """

    return any(ord(character) > 127 for character in value)
