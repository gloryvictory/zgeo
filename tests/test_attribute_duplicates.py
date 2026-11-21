import unittest

from zgeo.attribute_duplicates import (
    DUPLICATE_FULL_ROW,
    DUPLICATE_KEY,
    DUPLICATE_NORMALIZED,
    DUPLICATE_PARTIAL,
    AttributeDuplicate,
    attribute_duplicate_issues,
    find_attribute_duplicates,
    normalize_value,
)


class NormalizeValueTests(unittest.TestCase):
    def test_case_and_spaces_are_ignored(self) -> None:
        self.assertEqual(normalize_value("Москва"), normalize_value("москва "))
        self.assertEqual(normalize_value("  New   York "), "new york")

    def test_none_becomes_empty(self) -> None:
        self.assertEqual(normalize_value(None), "")


class FullRowTests(unittest.TestCase):
    def test_identical_rows_are_reported(self) -> None:
        rows = [
            ("Москва", 1),
            ("Тверь", 2),
            ("Москва", 1),
        ]
        duplicates = find_attribute_duplicates(
            ["name", "code"], rows, [1, 2, 3]
        )
        full = [
            item for item in duplicates if item.kind == DUPLICATE_FULL_ROW
        ]
        self.assertEqual(len(full), 1)
        self.assertEqual(full[0].count, 2)
        self.assertEqual(full[0].feature_ids, (1, 3))

    def test_unique_rows_are_not_reported(self) -> None:
        rows = [("Москва", 1), ("Тверь", 2)]
        duplicates = find_attribute_duplicates(
            ["name", "code"], rows, [1, 2]
        )
        self.assertEqual(
            [item for item in duplicates if item.kind == DUPLICATE_FULL_ROW],
            [],
        )


class CompositeKeyTests(unittest.TestCase):
    def test_identical_text_columns_are_reported(self) -> None:
        rows = [
            ("Москва", "RU", 10),
            ("Москва", "RU", 20),
            ("Тверь", "RU", 30),
        ]
        duplicates = find_attribute_duplicates(
            ["name", "country", "population"], rows, [1, 2, 3]
        )
        key = [item for item in duplicates if item.kind == DUPLICATE_KEY]
        self.assertEqual(len(key), 1)
        self.assertEqual(key[0].feature_ids, (1, 2))

    def test_all_text_layer_has_no_key_duplicates(self) -> None:
        rows = [("Москва", "RU"), ("Москва", "RU")]
        duplicates = find_attribute_duplicates(
            ["name", "country"], rows, [1, 2]
        )
        self.assertEqual(
            [item for item in duplicates if item.kind == DUPLICATE_KEY],
            [],
        )


class NormalizedDuplicateTests(unittest.TestCase):
    def test_case_and_trailing_space_match(self) -> None:
        rows = [("Москва",), ("москва ",), ("Тверь",)]
        duplicates = find_attribute_duplicates(["name"], rows, [1, 2, 3])
        normalized = [
            item
            for item in duplicates
            if item.kind == DUPLICATE_NORMALIZED
        ]
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0].field, "name")
        self.assertEqual(normalized[0].count, 2)
        self.assertEqual(normalized[0].feature_ids, (1, 2))
        self.assertIn("Москва", normalized[0].values)

    def test_distinct_values_are_not_reported(self) -> None:
        rows = [("Москва",), ("Тверь",)]
        duplicates = find_attribute_duplicates(["name"], rows, [1, 2])
        self.assertEqual(
            [
                item
                for item in duplicates
                if item.kind == DUPLICATE_NORMALIZED
            ],
            [],
        )


class PartialDuplicateTests(unittest.TestCase):
    def test_contained_value_is_reported_with_percent(self) -> None:
        short = "ЯмалоНенецкий автономный окру"
        long = "ЯмалоНенецкий автономный округ"
        rows = [(short,), (long,)]
        duplicates = find_attribute_duplicates(["name"], rows, [1, 2])
        partial = [
            item for item in duplicates if item.kind == DUPLICATE_PARTIAL
        ]
        self.assertEqual(len(partial), 1)
        expected = round(len(short) * 100.0 / len(long), 1)
        self.assertEqual(partial[0].percent, expected)
        self.assertEqual(partial[0].values, (short, long))
        self.assertIn(1, partial[0].feature_ids)
        self.assertIn(2, partial[0].feature_ids)

    def test_short_values_are_skipped(self) -> None:
        rows = [("ab",), ("abc",)]
        duplicates = find_attribute_duplicates(["name"], rows, [1, 2])
        self.assertEqual(
            [item for item in duplicates if item.kind == DUPLICATE_PARTIAL],
            [],
        )

    def test_containment_ignores_case(self) -> None:
        rows = [("автономный окру",), ("Автономный округ",)]
        duplicates = find_attribute_duplicates(["name"], rows, [1, 2])
        partial = [
            item for item in duplicates if item.kind == DUPLICATE_PARTIAL
        ]
        self.assertEqual(len(partial), 1)
        self.assertEqual(partial[0].values[0], "автономный окру")

    def test_low_percent_containment_is_skipped(self) -> None:
        rows = [("Москва",), ("Москва и Московская область",)]
        duplicates = find_attribute_duplicates(["name"], rows, [1, 2])
        self.assertEqual(
            [item for item in duplicates if item.kind == DUPLICATE_PARTIAL],
            [],
        )


class IssueTests(unittest.TestCase):
    def test_issue_messages_render(self) -> None:
        duplicates = [
            AttributeDuplicate(
                kind=DUPLICATE_FULL_ROW, feature_ids=(1, 2)
            ),
            AttributeDuplicate(
                kind=DUPLICATE_KEY, feature_ids=(3, 4)
            ),
            AttributeDuplicate(
                kind=DUPLICATE_NORMALIZED,
                field="name",
                values=("Москва", "москва "),
                feature_ids=(5, 6),
            ),
            AttributeDuplicate(
                kind=DUPLICATE_PARTIAL,
                field="name",
                values=("окру", "округ"),
                feature_ids=(7, 8),
                percent=80.0,
            ),
        ]
        issues = attribute_duplicate_issues("layer", duplicates, 10)
        self.assertEqual(len(issues), 4)
        for issue in issues:
            self.assertEqual(issue.check, "attribute_duplicates")
            rendered = issue.message.format(*issue.args)
            self.assertNotIn("{}", rendered)
            self.assertIn("layer", rendered)
        self.assertIn("80.0", issues[3].message.format(*issues[3].args))
        self.assertIn("объектов 2", issues[0].message.format(*issues[0].args))

    def test_empty_input_has_no_issues(self) -> None:
        self.assertEqual(find_attribute_duplicates([], [], []), [])
        self.assertEqual(
            find_attribute_duplicates(["name"], [("a",)], [1]), []
        )


if __name__ == "__main__":
    unittest.main()
