import unittest

from zgeo.attribute_check import (
    control_characters,
    control_character_label,
    date_year_out_of_range,
    edge_whitespace,
    escape_control_characters,
    escape_mojibake,
    looks_like_mojibake,
    repair_mojibake,
    escape_edge_whitespace,
    escape_inner_spaces,
    has_inner_spaces,
    inner_space_runs,
    looks_numeric_text,
    numeric_text_kind,
    parse_date_text,
    has_non_latin_characters,
    is_control_or_invisible,
)


class AttributeCheckTests(unittest.TestCase):
    def test_latin_names_and_common_separators_are_allowed(self) -> None:
        for name in ("name", "OBJECTID", "field_1", "field with space"):
            with self.subTest(name=name):
                self.assertFalse(has_non_latin_characters(name))

    def test_cyrillic_and_other_non_ascii_names_are_reported(self) -> None:
        for name in ("Наименование", "площадь", "naïve", "名称"):
            with self.subTest(name=name):
                self.assertTrue(has_non_latin_characters(name))

    def test_empty_name_has_no_problem(self) -> None:
        self.assertFalse(has_non_latin_characters(""))


class DateParsingTests(unittest.TestCase):
    def test_iso_and_european_dates_are_parsed(self) -> None:
        for value, expected in (
            ("2024-05-01", (2024, 5, 1)),
            ("01.05.2024", (2024, 5, 1)),
            ("01/05/2024", (2024, 5, 1)),
            ("2024/05/01", (2024, 5, 1)),
            ("2024-05-01T10:20:30", (2024, 5, 1)),
            ("2024-05-01 10:20", (2024, 5, 1)),
        ):
            with self.subTest(value=value):
                self.assertEqual(parse_date_text(value), expected)

    def test_zero_date_is_parsed(self) -> None:
        self.assertEqual(parse_date_text("0000-00-00"), (0, 0, 0))

    def test_invalid_dates_are_rejected(self) -> None:
        for value in ("abc", "", "31.02.2024", "2024-13-01", "2024-05",
                      "01-05-24", "2024-05-01-01"):
            with self.subTest(value=value):
                self.assertIsNone(parse_date_text(value))

    def test_out_of_range_years(self) -> None:
        self.assertEqual(
            date_year_out_of_range("1899-12-30", max_year=2026), 1899
        )
        self.assertEqual(
            date_year_out_of_range("0000-00-00", max_year=2026), 0
        )
        self.assertEqual(
            date_year_out_of_range("2999-01-01", max_year=2026), 2999
        )
        self.assertIsNone(
            date_year_out_of_range("2024-05-01", max_year=2026)
        )
        self.assertIsNone(date_year_out_of_range("abc", max_year=2026))


class MojibakeTests(unittest.TestCase):
    def test_latin1_mojibake_is_repaired(self) -> None:
        broken = "Москва".encode("utf-8").decode("latin-1")
        self.assertTrue(looks_like_mojibake(broken))
        self.assertEqual(repair_mojibake(broken), "Москва")

    def test_cp1251_mojibake_is_repaired(self) -> None:
        broken = "Привет мир".encode("utf-8").decode("cp1251")
        self.assertTrue(looks_like_mojibake(broken))
        self.assertEqual(repair_mojibake(broken), "Привет мир")

    def test_marker_based_detection(self) -> None:
        self.assertTrue(looks_like_mojibake("ÐœÐ¾ÑÐºÐ²Ð°"))
        self.assertTrue(looks_like_mojibake("ÐŸÑ€Ð¸Ð²ÐµÑ‚"))

    def test_clean_text_is_not_reported(self) -> None:
        for value in ("Москва", "ESPAÑA", "café", "Привет", "hello", ""):
            with self.subTest(value=value):
                self.assertFalse(looks_like_mojibake(value))
                self.assertEqual(repair_mojibake(value), "")

    def test_plain_latin_is_skipped(self) -> None:
        self.assertFalse(looks_like_mojibake("Moscow"))
        self.assertEqual(repair_mojibake("Moscow"), "")

    def test_escape_is_truncated(self) -> None:
        escaped = escape_mojibake("x" * 100, limit=10)
        self.assertEqual(escaped, "x" * 10 + "…")
        self.assertEqual(escape_mojibake("  short  "), "short")


class NumericTextTests(unittest.TestCase):
    def test_integers_are_detected(self) -> None:
        for value in ("10", "9", "007", "-12", "+7", " 42 "):
            with self.subTest(value=value):
                self.assertEqual(numeric_text_kind(value), "integer")
                self.assertTrue(looks_numeric_text(value))

    def test_real_numbers_are_detected(self) -> None:
        for value in ("12.5", "3,14", "1e5", "1.2e-3", ".5", "5."):
            with self.subTest(value=value):
                self.assertEqual(numeric_text_kind(value), "real")

    def test_non_numeric_values_are_skipped(self) -> None:
        for value in ("abc", "", "   ", "1 234", "1.2.3", "12a", "e5", "-"):
            with self.subTest(value=value):
                self.assertEqual(numeric_text_kind(value), "")
                self.assertFalse(looks_numeric_text(value))


class InnerSpaceTests(unittest.TestCase):
    def test_runs_inside_value_are_found(self) -> None:
        self.assertEqual(inner_space_runs("Москва  Сити"), (2,))
        self.assertEqual(inner_space_runs(" a  b   c "), (2, 3))
        self.assertEqual(inner_space_runs("Москва Сити"), ())
        self.assertEqual(inner_space_runs("   "), ())

    def test_has_inner_spaces(self) -> None:
        self.assertTrue(has_inner_spaces("улица  Ленина"))
        self.assertTrue(has_inner_spaces("a\t\tb"))
        self.assertFalse(has_inner_spaces("улица Ленина"))
        self.assertFalse(has_inner_spaces(""))

    def test_escape_shows_visible_symbols(self) -> None:
        self.assertEqual(
            escape_inner_spaces("Москва  Сити"), "«Москва··Сити»"
        )
        self.assertEqual(
            escape_inner_spaces("a\tb"), "«a\\tb»"
        )

    def test_escape_is_truncated(self) -> None:
        escaped = escape_inner_spaces("x" * 100, limit=10)
        self.assertEqual(len(escaped), 11)
        self.assertTrue(escaped.endswith("…"))


class EdgeWhitespaceTests(unittest.TestCase):
    def test_edge_whitespace_is_split(self) -> None:
        self.assertEqual(edge_whitespace("  Москва "), ("  ", " "))
        self.assertEqual(edge_whitespace("\tТверь\n"), ("\t", "\n"))
        self.assertEqual(edge_whitespace("Москва"), ("", ""))

    def test_whitespace_only_value(self) -> None:
        self.assertEqual(edge_whitespace("   "), ("   ", ""))

    def test_escape_shows_visible_symbols(self) -> None:
        self.assertEqual(escape_edge_whitespace("  Москва "), "··«Москва»·")
        self.assertEqual(
            escape_edge_whitespace("\tТверь"), "\\t«Тверь»"
        )
        self.assertEqual(escape_edge_whitespace("Москва"), "«Москва»")

    def test_escape_is_truncated(self) -> None:
        escaped = escape_edge_whitespace("  " + "x" * 100, limit=10)
        self.assertEqual(len(escaped), 11)
        self.assertTrue(escaped.endswith("…"))


class ControlCharacterTests(unittest.TestCase):
    def test_control_characters_are_detected(self) -> None:
        for character in ("\t", "\n", "\r", "\v", "\f", "\x00", "\x1b"):
            with self.subTest(character=repr(character)):
                self.assertTrue(is_control_or_invisible(character))

    def test_invisible_characters_are_detected(self) -> None:
        for character in (
            "\u00a0",
            "\u00ad",
            "\u200b",
            "\u200c",
            "\u200d",
            "\u2028",
            "\u2029",
            "\u202f",
            "\u2060",
            "\ufeff",
            "\u2007",
        ):
            with self.subTest(character=repr(character)):
                self.assertTrue(is_control_or_invisible(character))

    def test_regular_text_is_allowed(self) -> None:
        for character in (" ", "a", "Я", "1", "_", "-", "."):
            with self.subTest(character=character):
                self.assertFalse(is_control_or_invisible(character))

    def test_control_characters_are_unique_and_ordered(self) -> None:
        self.assertEqual(
            control_characters("a\tb\tc\nd"),
            ("\t", "\n"),
        )
        self.assertEqual(control_characters("plain text"), ())

    def test_labels_use_names_and_code_points(self) -> None:
        self.assertEqual(control_character_label("\t"), "TAB (U+0009)")
        self.assertEqual(control_character_label("\n"), "LF (U+000A)")
        self.assertEqual(control_character_label("\u00a0"), "NBSP (U+00A0)")
        self.assertEqual(control_character_label("\u2007"), "U+2007")

    def test_escape_shows_visible_placeholders(self) -> None:
        self.assertEqual(
            escape_control_characters("a\tb\nc"), "a\\tb\\nc"
        )
        self.assertEqual(
            escape_control_characters("a\u00a0b"), "a\\u00a0b"
        )
        self.assertEqual(escape_control_characters("plain"), "plain")

    def test_escape_is_truncated(self) -> None:
        escaped = escape_control_characters("x" * 200, limit=10)
        self.assertEqual(escaped, "x" * 10 + "…")


if __name__ == "__main__":
    unittest.main()
