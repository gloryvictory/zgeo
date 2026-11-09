"""Проверки переключения языка и перевода строк."""

from __future__ import annotations

import unittest

from zgeo.formatting import format_size
from zgeo.i18n import (
    LANGUAGE_EN,
    LANGUAGE_RU,
    category_label,
    get_language,
    normalize_language,
    set_language,
    tr,
)
from zgeo.stats import build_size_distribution


class I18nTests(unittest.TestCase):
    def setUp(self) -> None:
        set_language(LANGUAGE_RU)

    def tearDown(self) -> None:
        set_language(LANGUAGE_RU)

    def test_russian_is_default_and_source_language(self) -> None:
        self.assertEqual(get_language(), LANGUAGE_RU)
        self.assertEqual(tr("Выбрать папку"), "Выбрать папку")

    def test_english_translation_and_formatting(self) -> None:
        set_language(LANGUAGE_EN)
        self.assertEqual(tr("Выбрать папку"), "Select folder")
        self.assertEqual(
            tr("Файлов: {} · {}", 3, "1.5 МБ"),
            "Files: 3 · 1.5 МБ",
        )

    def test_language_normalization(self) -> None:
        self.assertEqual(normalize_language("EN"), LANGUAGE_EN)
        self.assertEqual(normalize_language("en_US"), LANGUAGE_EN)
        self.assertEqual(normalize_language("ru"), LANGUAGE_RU)
        self.assertEqual(normalize_language(None), LANGUAGE_RU)

    def test_category_labels(self) -> None:
        self.assertEqual(category_label("vector"), "Векторные данные")
        set_language(LANGUAGE_EN)
        self.assertEqual(category_label("vector"), "Vector data")
        self.assertEqual(category_label("unknown"), "unknown")

    def test_size_units_follow_language(self) -> None:
        self.assertEqual(format_size(1536), "1.5 КБ")
        set_language(LANGUAGE_EN)
        self.assertEqual(format_size(1536), "1.5 KB")
        self.assertEqual(format_size(1024 ** 2), "1 MB")

    def test_size_buckets_follow_language(self) -> None:
        self.assertEqual(
            build_size_distribution([])[0].label, "До 1 МБ"
        )
        set_language(LANGUAGE_EN)
        self.assertEqual(
            build_size_distribution([])[0].label, "Up to 1 MB"
        )


if __name__ == "__main__":
    unittest.main()
