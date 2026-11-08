import unittest

from zgeo.attribute_check import has_non_latin_characters


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


if __name__ == "__main__":
    unittest.main()
