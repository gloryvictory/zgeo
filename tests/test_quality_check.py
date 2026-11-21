"""Проверки качества полей, набора данных и слоёв."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from zgeo.quality_check import (
    CrsDescriptor,
    FieldBlankStats,
    FieldControlStats,
    FieldDateRangeStats,
    FieldEdgeSpaceStats,
    FieldInnerSpaceStats,
    FieldNumericTextStats,
    FieldTextLengthStats,
    FieldFillStats,
    LayerBlankStats,
    LayerControlStats,
    LayerDateRangeStats,
    LayerEdgeSpaceStats,
    LayerInnerSpaceStats,
    LayerNumericTextStats,
    LayerTextLengthStats,
    LayerFillStats,
    ReadabilityProblem,
    TopologyStats,
    attribute_fill_issues,
    blank_string_issues,
    case_insensitive_duplicate_issues,
    completeness_issues,
    control_character_issues,
    coordinate_problem,
    crs_issues,
    date_range_issues,
    crs_metadata_issues,
    dbf_encoding_issues,
    directory_files,
    duplicate_geometry_issues,
    edge_space_issues,
    inner_space_issues,
    length_outlier_positions,
    length_statistics,
    numeric_text_issues,
    text_length_issues,
    file_path_issues,
    invalid_name_characters,
    is_reserved_file_name,
    orphan_sidecars,
    field_name_issues,
    file_path_issues,
    invalid_name_characters,
    is_known_encoding,
    is_reserved_file_name,
    orphan_sidecars,
    metadata_sidecar_issues,
    prj_file_issues,
    readability_issues,
    suspicious_field_name_issues,
    suspicious_field_name_reason,
    topology_summary_issues,
    truncated_duplicate_issues,
)


def geo_file(path: Path):
    return SimpleNamespace(path=path, extension=path.suffix.lower())


class SuspiciousFieldNameTests(unittest.TestCase):
    def test_reasons(self) -> None:
        cases = {
            "NULL": "null",
            "none": "null",
            "NAN": "null",
            "Field1": "filler",
            "field_2": "filler",
            "Unnamed: 0": "filler",
            "Column3": "filler",
            "Attribute1": "filler",
            "2024": "numeric",
            "": "empty",
            "   ": "empty",
            "name": "",
            "OBJECTID": "",
            "id": "",
        }
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(
                    suspicious_field_name_reason(name), expected
                )

    def test_issues_are_reported_per_field(self) -> None:
        issues = suspicious_field_name_issues(
            [("layer", ("NULL", "Field1", "name", "2024"))]
        )
        self.assertEqual(len(issues), 3)
        locations = [issue.location for issue in issues]
        self.assertEqual(locations, ["NULL", "Field1", "2024"])
        for issue in issues:
            self.assertEqual(
                issue.check, "suspicious_field_names"
            )
            rendered = issue.message.format(*issue.args)
            self.assertIn("layer", rendered)
            self.assertNotIn("name", rendered)

    def test_empty_name_is_reported_with_placeholder(self) -> None:
        issues = suspicious_field_name_issues([("layer", ("", ""))])
        self.assertEqual(len(issues), 2)
        self.assertEqual(
            [issue.location for issue in issues], ["Поле 1", "Поле 2"]
        )
        rendered = issues[0].message.format(*issues[0].args)
        self.assertIn("—", rendered)

    def test_clean_names_have_no_issues(self) -> None:
        self.assertEqual(
            suspicious_field_name_issues(
                [("layer", ("id", "code", "name", "OBJECTID"))]
            ),
            [],
        )


class DateRangeTests(unittest.TestCase):
    def test_fields_with_out_of_range_dates_are_reported(self) -> None:
        layer = LayerDateRangeStats(
            layer="events",
            feature_count=5,
            fields=(
                FieldDateRangeStats(
                    name="date",
                    total=5,
                    invalid=((1, "1899-12-30"), (3, "0000-00-00")),
                    earliest=0,
                    latest=1899,
                ),
                FieldDateRangeStats(name="name", total=5),
            ),
        )
        issues = date_range_issues([layer])
        self.assertEqual(len(issues), 2)
        summary = issues[0]
        self.assertEqual(summary.check, "date_range")
        rendered = summary.message.format(*summary.args)
        self.assertIn("date — 2 из 5", rendered)
        self.assertNotIn("name", rendered)
        detail = issues[1]
        self.assertTrue(detail.detail_only)
        self.assertEqual(detail.location, "date")
        text = detail.message.format(*detail.args)
        self.assertIn("40%", text)
        self.assertIn("1899", text)
        self.assertIn("1899-12-30", text)
        self.assertIn("0000-00-00", text)

    def test_clean_layer_has_no_issues(self) -> None:
        layer = LayerDateRangeStats(
            layer="events",
            feature_count=5,
            fields=(FieldDateRangeStats(name="date", total=5),),
        )
        self.assertEqual(date_range_issues([layer]), [])

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerDateRangeStats(
            layer="events", feature_count=0, fields=()
        )
        self.assertEqual(date_range_issues([layer]), [])

    def test_field_list_is_truncated(self) -> None:
        fields = tuple(
            FieldDateRangeStats(
                name="f{}".format(index),
                total=10,
                invalid=((1, "1899-12-30"),),
            )
            for index in range(12)
        )
        layer = LayerDateRangeStats(
            layer="events", feature_count=10, fields=fields
        )
        issues = date_range_issues([layer], field_limit=3)
        self.assertIn("…", issues[0].args[3])
        self.assertEqual(len(issues), 1 + 12)

    def test_totals_and_share(self) -> None:
        layer = LayerDateRangeStats(
            layer="events",
            feature_count=4,
            fields=(
                FieldDateRangeStats(
                    name="a", total=4, invalid=((1, "1899-01-01"),)
                ),
                FieldDateRangeStats(
                    name="b",
                    total=4,
                    invalid=((2, "1898-01-01"), (3, "2999-01-01")),
                ),
                FieldDateRangeStats(name="c", total=4),
            ),
        )
        self.assertEqual(layer.invalid_total, 3)
        self.assertEqual(layer.affected_fields, 2)
        self.assertAlmostEqual(layer.fields[1].share, 0.5)


class TextLengthTests(unittest.TestCase):
    def test_statistics(self) -> None:
        mean, deviation = length_statistics([2, 4, 6])
        self.assertAlmostEqual(mean, 4.0)
        self.assertAlmostEqual(deviation, (8 / 3) ** 0.5)
        self.assertEqual(length_statistics([]), (0.0, 0.0))

    def test_outlier_positions(self) -> None:
        lengths = [6] * 11 + [40]
        self.assertEqual(length_outlier_positions(lengths), (11,))

    def test_single_value_among_few_is_not_flagged(self) -> None:
        lengths = [6, 6, 6, 6, 6, 6, 6, 6, 40]
        self.assertEqual(length_outlier_positions(lengths), ())

    def test_short_samples_and_equal_lengths(self) -> None:
        self.assertEqual(length_outlier_positions([1, 40]), ())
        self.assertEqual(length_outlier_positions([5, 5, 5, 5]), ())

    def test_fields_with_outliers_are_reported(self) -> None:
        layer = LayerTextLengthStats(
            layer="roads",
            feature_count=9,
            fields=(
                FieldTextLengthStats(
                    name="name",
                    total=9,
                    outliers=((7, 40),),
                    mean=7.8,
                    deviation=11.3,
                    example="«Москва, Тверь»",
                ),
                FieldTextLengthStats(name="code", total=9),
            ),
        )
        issues = text_length_issues([layer])
        self.assertEqual(len(issues), 2)
        summary = issues[0]
        self.assertEqual(summary.check, "text_length")
        rendered = summary.message.format(*summary.args)
        self.assertIn("name — 1 из 9", rendered)
        self.assertNotIn("code", rendered)
        detail = issues[1]
        self.assertTrue(detail.detail_only)
        self.assertEqual(detail.location, "name")
        text = detail.message.format(*detail.args)
        self.assertIn("40", text)
        self.assertIn("объекты: 7", text)
        self.assertIn("Москва", text)
        self.assertIn("среднее 7.8", text)

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerTextLengthStats(
            layer="roads", feature_count=0, fields=()
        )
        self.assertEqual(text_length_issues([layer]), [])

    def test_field_list_is_truncated(self) -> None:
        fields = tuple(
            FieldTextLengthStats(
                name="f{}".format(index),
                total=10,
                outliers=((1, 30),),
            )
            for index in range(12)
        )
        layer = LayerTextLengthStats(
            layer="roads", feature_count=10, fields=fields
        )
        issues = text_length_issues([layer], field_limit=3)
        self.assertIn("…", issues[0].args[3])
        self.assertEqual(len(issues), 1 + 12)

    def test_totals_and_share(self) -> None:
        layer = LayerTextLengthStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldTextLengthStats(
                    name="a", total=4, outliers=((1, 30),)
                ),
                FieldTextLengthStats(
                    name="b", total=4, outliers=((2, 20), (3, 25))
                ),
                FieldTextLengthStats(name="c", total=4),
            ),
        )
        self.assertEqual(layer.outlier_total, 3)
        self.assertEqual(layer.affected_fields, 2)
        self.assertAlmostEqual(layer.fields[1].share, 0.5)
        self.assertEqual(layer.fields[1].longest, 25)


class NumericTextTests(unittest.TestCase):
    def test_fields_with_numeric_text_are_reported(self) -> None:
        layer = LayerNumericTextStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldNumericTextStats(
                    name="code",
                    total=4,
                    numeric=3,
                    integer=2,
                    real=1,
                    example="10",
                ),
                FieldNumericTextStats(name="name", total=4, numeric=0),
            ),
        )
        issues = numeric_text_issues([layer])
        self.assertEqual(len(issues), 2)
        summary = issues[0]
        self.assertEqual(summary.check, "numeric_text")
        rendered = summary.message.format(*summary.args)
        self.assertIn("code — 3 из 4", rendered)
        self.assertNotIn("name", rendered)
        detail = issues[1]
        self.assertTrue(detail.detail_only)
        self.assertEqual(detail.location, "code")
        text = detail.message.format(*detail.args)
        self.assertIn("75%", text)
        self.assertIn("целых 2", text)
        self.assertIn("дробных 1", text)
        self.assertIn("«10»", text)

    def test_clean_layer_has_no_issues(self) -> None:
        layer = LayerNumericTextStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldNumericTextStats(name="name", total=4, numeric=0),
            ),
        )
        self.assertEqual(numeric_text_issues([layer]), [])

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerNumericTextStats(
            layer="roads", feature_count=0, fields=()
        )
        self.assertEqual(numeric_text_issues([layer]), [])

    def test_field_list_is_truncated(self) -> None:
        fields = tuple(
            FieldNumericTextStats(
                name="f{}".format(index), total=10, numeric=1
            )
            for index in range(12)
        )
        layer = LayerNumericTextStats(
            layer="roads", feature_count=10, fields=fields
        )
        issues = numeric_text_issues([layer], field_limit=3)
        self.assertIn("…", issues[0].args[3])
        self.assertEqual(len(issues), 1 + 12)

    def test_totals_and_share(self) -> None:
        layer = LayerNumericTextStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldNumericTextStats(name="a", total=4, numeric=1),
                FieldNumericTextStats(name="b", total=4, numeric=3),
                FieldNumericTextStats(name="c", total=4, numeric=0),
            ),
        )
        self.assertEqual(layer.numeric_total, 4)
        self.assertEqual(layer.affected_fields, 2)
        self.assertAlmostEqual(layer.fields[1].share, 0.75)


class InnerSpaceTests(unittest.TestCase):
    def test_fields_with_inner_spaces_are_reported(self) -> None:
        layer = LayerInnerSpaceStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldInnerSpaceStats(
                    name="name",
                    total=4,
                    affected=2,
                    example="«Москва··Сити»",
                ),
                FieldInnerSpaceStats(name="code", total=4, affected=0),
            ),
        )
        issues = inner_space_issues([layer])
        self.assertEqual(len(issues), 2)
        summary = issues[0]
        self.assertEqual(summary.check, "inner_spaces")
        rendered = summary.message.format(*summary.args)
        self.assertIn("name — 2 из 4", rendered)
        self.assertNotIn("code", rendered)
        detail = issues[1]
        self.assertTrue(detail.detail_only)
        self.assertEqual(detail.location, "name")
        text = detail.message.format(*detail.args)
        self.assertIn("50%", text)
        self.assertIn("Москва", text)

    def test_clean_layer_has_no_issues(self) -> None:
        layer = LayerInnerSpaceStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldInnerSpaceStats(name="name", total=4, affected=0),
            ),
        )
        self.assertEqual(inner_space_issues([layer]), [])

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerInnerSpaceStats(
            layer="roads", feature_count=0, fields=()
        )
        self.assertEqual(inner_space_issues([layer]), [])

    def test_field_list_is_truncated(self) -> None:
        fields = tuple(
            FieldInnerSpaceStats(
                name="f{}".format(index), total=10, affected=1
            )
            for index in range(12)
        )
        layer = LayerInnerSpaceStats(
            layer="roads", feature_count=10, fields=fields
        )
        issues = inner_space_issues([layer], field_limit=3)
        self.assertIn("…", issues[0].args[3])
        self.assertEqual(len(issues), 1 + 12)

    def test_totals_and_share(self) -> None:
        layer = LayerInnerSpaceStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldInnerSpaceStats(name="a", total=4, affected=1),
                FieldInnerSpaceStats(name="b", total=4, affected=3),
                FieldInnerSpaceStats(name="c", total=4, affected=0),
            ),
        )
        self.assertEqual(layer.affected_total, 4)
        self.assertEqual(layer.affected_fields, 2)
        self.assertAlmostEqual(layer.fields[1].share, 0.75)


class EdgeSpaceTests(unittest.TestCase):
    def test_fields_with_edge_spaces_are_reported(self) -> None:
        layer = LayerEdgeSpaceStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldEdgeSpaceStats(
                    name="name",
                    total=4,
                    affected=2,
                    leading=1,
                    trailing=2,
                    example="·Москва·",
                ),
                FieldEdgeSpaceStats(name="code", total=4, affected=0),
            ),
        )
        issues = edge_space_issues([layer])
        self.assertEqual(len(issues), 2)
        summary = issues[0]
        self.assertEqual(summary.check, "edge_spaces")
        rendered = summary.message.format(*summary.args)
        self.assertIn("name — 2 из 4", rendered)
        self.assertNotIn("code", rendered)
        detail = issues[1]
        self.assertTrue(detail.detail_only)
        self.assertEqual(detail.location, "name")
        text = detail.message.format(*detail.args)
        self.assertIn("50%", text)
        self.assertIn("в начале 1", text)
        self.assertIn("в конце 2", text)
        self.assertIn("·Москва·", text)

    def test_clean_layer_has_no_issues(self) -> None:
        layer = LayerEdgeSpaceStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldEdgeSpaceStats(name="name", total=4, affected=0),
            ),
        )
        self.assertEqual(edge_space_issues([layer]), [])

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerEdgeSpaceStats(
            layer="roads", feature_count=0, fields=()
        )
        self.assertEqual(edge_space_issues([layer]), [])

    def test_field_list_is_truncated(self) -> None:
        fields = tuple(
            FieldEdgeSpaceStats(
                name="f{}".format(index), total=10, affected=1
            )
            for index in range(12)
        )
        layer = LayerEdgeSpaceStats(
            layer="roads", feature_count=10, fields=fields
        )
        issues = edge_space_issues([layer], field_limit=3)
        self.assertIn("…", issues[0].args[3])
        self.assertEqual(len(issues), 1 + 12)

    def test_totals_and_share(self) -> None:
        layer = LayerEdgeSpaceStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldEdgeSpaceStats(name="a", total=4, affected=1),
                FieldEdgeSpaceStats(name="b", total=4, affected=3),
                FieldEdgeSpaceStats(name="c", total=4, affected=0),
            ),
        )
        self.assertEqual(layer.affected_total, 4)
        self.assertEqual(layer.affected_fields, 2)
        self.assertAlmostEqual(layer.fields[1].share, 0.75)


class BlankStringTests(unittest.TestCase):
    def test_blank_fields_are_reported(self) -> None:
        layer = LayerBlankStats(
            layer="roads",
            feature_count=200,
            fields=(
                FieldBlankStats(name="name", total=200, blank=12),
                FieldBlankStats(name="code", total=200, blank=0),
            ),
        )
        issues = blank_string_issues([layer])
        self.assertEqual(len(issues), 2)
        summary = issues[0]
        self.assertEqual(summary.check, "blank_strings")
        rendered = summary.message.format(*summary.args)
        self.assertIn("name — 12 из 200", rendered)
        self.assertNotIn("code", rendered)
        detail = issues[1]
        self.assertTrue(detail.detail_only)
        self.assertEqual(detail.location, "name")
        self.assertIn("6%", detail.message.format(*detail.args))

    def test_clean_layer_has_no_issues(self) -> None:
        layer = LayerBlankStats(
            layer="roads",
            feature_count=10,
            fields=(FieldBlankStats(name="name", total=10, blank=0),),
        )
        self.assertEqual(blank_string_issues([layer]), [])

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerBlankStats(
            layer="roads",
            feature_count=0,
            fields=(FieldBlankStats(name="name", total=0, blank=0),),
        )
        self.assertEqual(blank_string_issues([layer]), [])

    def test_field_list_is_truncated(self) -> None:
        fields = tuple(
            FieldBlankStats(name="f{}".format(index), total=10, blank=1)
            for index in range(12)
        )
        layer = LayerBlankStats(
            layer="roads", feature_count=10, fields=fields
        )
        issues = blank_string_issues([layer], field_limit=3)
        self.assertIn("…", issues[0].args[3])
        self.assertEqual(len(issues), 1 + 12)

    def test_share_and_totals(self) -> None:
        layer = LayerBlankStats(
            layer="roads",
            feature_count=4,
            fields=(
                FieldBlankStats(name="a", total=4, blank=1),
                FieldBlankStats(name="b", total=4, blank=3),
                FieldBlankStats(name="c", total=4, blank=0),
            ),
        )
        self.assertEqual(layer.blank_total, 4)
        self.assertEqual(layer.affected_fields, 2)
        self.assertAlmostEqual(layer.fields[1].share, 0.75)


class ControlCharacterTests(unittest.TestCase):
    def test_field_with_control_characters_is_reported(self) -> None:
        layer = LayerControlStats(
            layer="roads",
            feature_count=10,
            fields=(
                FieldControlStats(
                    name="name",
                    features_with_chars=3,
                    characters=("TAB (U+0009)", "LF (U+000A)"),
                    example="Иванов\\tИ.И.",
                ),
            ),
        )
        issues = control_character_issues([layer])
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.check, "control_chars")
        self.assertEqual(issue.layer, "roads")
        self.assertEqual(issue.location, "name")
        rendered = issue.message.format(*issue.args)
        self.assertIn("TAB (U+0009)", rendered)
        self.assertIn("3", rendered)
        self.assertIn("10", rendered)
        self.assertIn("Иванов", rendered)

    def test_clean_layer_has_no_issues(self) -> None:
        layer = LayerControlStats(
            layer="roads", feature_count=5, fields=()
        )
        self.assertEqual(control_character_issues([layer]), [])

    def test_character_list_is_truncated(self) -> None:
        layer = LayerControlStats(
            layer="roads",
            feature_count=2,
            fields=(
                FieldControlStats(
                    name="name",
                    features_with_chars=1,
                    characters=tuple(
                        "U+{:04X}".format(0x200B + index)
                        for index in range(8)
                    ),
                ),
            ),
        )
        issues = control_character_issues([layer])
        self.assertIn("…", issues[0].args[4])
        self.assertEqual(issues[0].args[4].count(","), 6)

    def test_empty_layer_is_skipped(self) -> None:
        layer = LayerControlStats(
            layer="roads",
            feature_count=0,
            fields=(FieldControlStats("name", 2, ("TAB (U+0009)",)),),
        )
        self.assertEqual(control_character_issues([layer]), [])

    def test_affected_features_and_fields(self) -> None:
        layer = LayerControlStats(
            layer="roads",
            feature_count=10,
            fields=(
                FieldControlStats("name", 3),
                FieldControlStats("code", 7),
                FieldControlStats("comment", 0),
            ),
        )
        self.assertEqual(layer.affected_features, 7)
        self.assertEqual(layer.affected_fields, 2)


class FieldNameTests(unittest.TestCase):
    def test_length_spaces_and_special_characters(self) -> None:
        issues = field_name_issues(
            [
                (
                    "layer",
                    (
                        "long_field_name",
                        "bad name",
                        "bad-name",
                        "ok_name",
                    ),
                )
            ]
        )
        rendered = [
            issue.message.format(*issue.args) for issue in issues
        ]
        self.assertTrue(
            any("длина 15" in message for message in rendered), rendered
        )
        self.assertTrue(
            any("«bad name»: содержит пробел" in message for message in rendered),
            rendered,
        )
        self.assertTrue(
            any("«bad-name»: недопустимые символы: -" in message for message in rendered),
            rendered,
        )
        self.assertFalse(
            any("ok_name" in message for message in rendered), rendered
        )

    def test_same_field_across_layers_is_reported_once(self) -> None:
        issues = field_name_issues(
            [
                ("one", ("very_long_field",)),
                ("two", ("very_long_field",)),
            ]
        )
        self.assertEqual(len(issues), 1)

    def test_case_insensitive_duplicates(self) -> None:
        issues = case_insensitive_duplicate_issues(
            [
                (
                    "layer",
                    (
                        "Name",
                        "name",
                        "NAME",
                        "other",
                    ),
                )
            ]
        )
        self.assertEqual(len(issues), 1)
        rendered = issues[0].message.format(*issues[0].args)
        self.assertIn("без учёта регистра", rendered)
        self.assertIn("Name", rendered)
        self.assertIn("name", rendered)
        self.assertIn("NAME", rendered)
        self.assertNotIn("other", rendered)

    def test_case_insensitive_duplicates_are_layer_specific(self) -> None:
        self.assertEqual(
            case_insensitive_duplicate_issues(
                [
                    ("one", ("Name",)),
                    ("two", ("name",)),
                ]
            ),
            [],
        )

    def test_no_case_insensitive_duplicates(self) -> None:
        self.assertEqual(
            case_insensitive_duplicate_issues(
                [("layer", ("Name", "title"))]
            ),
            [],
        )

    def test_truncated_duplicates(self) -> None:
        issues = truncated_duplicate_issues(
            [
                (
                    "layer",
                    (
                        "abcdefghij_one",
                        "abcdefghij_two",
                        "short_name",
                    ),
                )
            ]
        )
        self.assertEqual(len(issues), 1)
        rendered = issues[0].message.format(*issues[0].args)
        self.assertIn("abcdefghij", rendered)
        self.assertIn("abcdefghij_one", rendered)
        self.assertIn("abcdefghij_two", rendered)

    def test_no_truncated_duplicates_for_short_names(self) -> None:
        self.assertEqual(
            truncated_duplicate_issues(
                [("layer", ("one", "two", "three"))]
            ),
            [],
        )


class CompletenessTests(unittest.TestCase):
    def test_shapefile_requires_dbf_and_shx(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "roads.shp").write_bytes(b"shp")
            (root / "roads.dbf").write_bytes(b"dbf")
            files = directory_files(root, {})
            issues = completeness_issues(geo_file(root / "roads.shp"), files)
            rendered = issues[0].message.format(*issues[0].args)
            self.assertIn(".shx", rendered)
            self.assertNotIn(".dbf", rendered)

    def test_mif_requires_mid(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "plots.mif").write_bytes(b"mif")
            files = directory_files(root, {})
            issues = completeness_issues(geo_file(root / "plots.mif"), files)
            self.assertEqual(len(issues), 1)

    def test_tab_requires_mapinfo_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "table.tab").write_bytes(b"tab")
            (root / "table.dat").write_bytes(b"dat")
            (root / "table.map").write_bytes(b"map")
            files = directory_files(root, {})
            issues = completeness_issues(geo_file(root / "table.tab"), files)
            rendered = issues[0].message.format(*issues[0].args)
            self.assertIn(".id", rendered)
            self.assertNotIn(".dat", rendered)

    def test_case_insensitive_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "roads.shp").write_bytes(b"shp")
            (root / "ROADS.DBF").write_bytes(b"dbf")
            (root / "Roads.SHX").write_bytes(b"shx")
            files = directory_files(root, {})
            self.assertEqual(
                completeness_issues(geo_file(root / "roads.shp"), files),
                [],
            )


class DbfEncodingTests(unittest.TestCase):
    def _make_dbf(self, root: Path, ldid: int = 0) -> Path:
        header = bytearray(32)
        header[0] = 0x03
        header[29] = ldid
        path = root / "table.dbf"
        path.write_bytes(bytes(header))
        (root / "table.shp").write_bytes(b"shp")
        return path

    def test_missing_cpg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_dbf(root)
            files = directory_files(root, {})
            issues = dbf_encoding_issues(
                geo_file(root / "table.shp"), files
            )
            self.assertEqual(len(issues), 1)
            self.assertIn(".cpg", issues[0].message)

    def test_valid_cpg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_dbf(root, ldid=0xC9)
            (root / "table.cpg").write_text("1251", encoding="utf-8")
            files = directory_files(root, {})
            self.assertEqual(
                dbf_encoding_issues(geo_file(root / "table.shp"), files),
                [],
            )

    def test_empty_and_unknown_cpg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self._make_dbf(root)
            (root / "table.cpg").write_text("  ", encoding="utf-8")
            files = directory_files(root, {})
            issues = dbf_encoding_issues(
                geo_file(root / "table.shp"), files
            )
            self.assertIn("пуст", issues[0].message)

            (root / "table.cpg").write_text(
                "ANSI 1251", encoding="utf-8"
            )
            files = directory_files(root, {})
            issues = dbf_encoding_issues(
                geo_file(root / "table.shp"), files
            )
            self.assertIn("Неизвестная", issues[0].message)

    def test_short_dbf_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "table.shp").write_bytes(b"shp")
            (root / "table.dbf").write_bytes(b"short")
            files = directory_files(root, {})
            issues = dbf_encoding_issues(
                geo_file(root / "table.shp"), files
            )
            messages = [issue.message for issue in issues]
            self.assertIn("Не удалось прочитать заголовок DBF", messages)

    def test_known_encodings(self) -> None:
        for value in ("UTF-8", "utf8", "1251", "CP1251", "LDID/87"):
            with self.subTest(value=value):
                self.assertTrue(is_known_encoding(value))
        for value in ("", "ANSI 1251", "unknown"):
            with self.subTest(value=value):
                self.assertFalse(is_known_encoding(value))

    def test_non_shapefile_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "table.gpkg").write_bytes(b"gpkg")
            files = directory_files(root, {})
            self.assertEqual(
                dbf_encoding_issues(geo_file(root / "table.gpkg"), files),
                [],
            )


class CrsTests(unittest.TestCase):
    def test_no_layers(self) -> None:
        self.assertEqual(crs_issues([]), [])

    def test_missing_crs(self) -> None:
        issues = crs_issues(["Не определена"])
        self.assertEqual(len(issues), 1)
        self.assertIn("не определена", issues[0].message)

    def test_partially_missing_crs(self) -> None:
        issues = crs_issues(
            ["EPSG:4326 — WGS 84", "Не определена"]
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("У части слоёв", issues[0].message)

    def test_mixed_crs(self) -> None:
        issues = crs_issues(
            ["EPSG:4326 — WGS 84", "EPSG:3857 — Web Mercator"]
        )
        self.assertEqual(len(issues), 1)
        self.assertIn("Смешанные", issues[0].message)

    def test_missing_and_mixed_crs(self) -> None:
        issues = crs_issues(
            [
                "EPSG:4326 — WGS 84",
                "EPSG:3857 — Web Mercator",
                "Не определена",
            ]
        )
        messages = [issue.message for issue in issues]
        self.assertIn("У части слоёв не определена система координат", messages)
        self.assertIn("Смешанные системы координат: {}", messages)

    def test_single_crs(self) -> None:
        self.assertEqual(
            crs_issues(
                ["EPSG:4326 — WGS 84", "EPSG:4326 — WGS 84"]
            ),
            [],
        )


class MetadataSidecarTests(unittest.TestCase):
    def test_shapefile_missing_prj_and_cpg(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "roads.shp").write_bytes(b"shp")
            files = directory_files(root, {})
            issues = metadata_sidecar_issues(
                geo_file(root / "roads.shp"), files
            )
            messages = [
                issue.message.format(*issue.args) for issue in issues
            ]
            self.assertTrue(any(".prj" in message for message in messages))
            self.assertTrue(any(".cpg" in message for message in messages))

    def test_shapefile_cpg_can_be_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "roads.shp").write_bytes(b"shp")
            (root / "roads.prj").write_bytes(b"prj")
            files = directory_files(root, {})
            issues = metadata_sidecar_issues(
                geo_file(root / "roads.shp"),
                files,
                include_cpg=False,
            )
            self.assertEqual(issues, [])

    def test_shapefile_accepts_qpj_projection_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "roads.shp").write_bytes(b"shp")
            (root / "roads.qpj").write_bytes(b"qpj")
            (root / "roads.cpg").write_bytes(b"UTF-8")
            files = directory_files(root, {})
            self.assertEqual(
                metadata_sidecar_issues(
                    geo_file(root / "roads.shp"), files
                ),
                [],
            )

    def test_shapefile_complete_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "roads.shp").write_bytes(b"shp")
            (root / "roads.prj").write_bytes(b"prj")
            (root / "roads.cpg").write_bytes(b"UTF-8")
            files = directory_files(root, {})
            self.assertEqual(
                metadata_sidecar_issues(
                    geo_file(root / "roads.shp"), files
                ),
                [],
            )

    def test_raster_missing_auxiliary_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raster = SimpleNamespace(
                path=root / "dem.tif",
                extension=".tif",
                category="raster",
            )
            issues = metadata_sidecar_issues(raster, {}, has_crs=True)
            self.assertEqual(len(issues), 1)
            message = issues[0].message.format(*issues[0].args)
            self.assertIn(".aux.xml", message)
            self.assertIn(".ovr", message)

    def test_raster_without_crs_requires_world_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dem.aux.xml").write_bytes(b"aux")
            (root / "dem.ovr").write_bytes(b"ovr")
            raster = SimpleNamespace(
                path=root / "dem.tif",
                extension=".tif",
                category="raster",
            )
            files = directory_files(root, {})
            issues = metadata_sidecar_issues(
                raster, files, has_crs=False
            )
            self.assertEqual(len(issues), 1)
            self.assertIn(".tfw", issues[0].message)

    def test_raster_with_world_file_is_complete(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dem.tif").write_bytes(b"tif")
            (root / "dem.aux.xml").write_bytes(b"aux")
            (root / "dem.ovr").write_bytes(b"ovr")
            (root / "dem.tfw").write_bytes(b"tfw")
            raster = SimpleNamespace(
                path=root / "dem.tif",
                extension=".tif",
                category="raster",
            )
            files = directory_files(root, {})
            self.assertEqual(
                metadata_sidecar_issues(
                    raster, files, has_crs=False
                ),
                [],
            )

    def test_non_raster_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            vector = SimpleNamespace(
                path=root / "data.geojson",
                extension=".geojson",
                category="vector",
            )
            self.assertEqual(
                metadata_sidecar_issues(vector, {}),
                [],
            )


class CrsMetadataTests(unittest.TestCase):
    def descriptor(self, **overrides) -> CrsDescriptor:
        values = {
            "layer": "layer",
            "authid": "EPSG:3857",
            "description": "WGS 84 / Pseudo-Mercator",
            "valid": True,
            "geographic": False,
            "projected": True,
            "deprecated": False,
            "units": "Meters",
            "axis_inverted": False,
        }
        values.update(overrides)
        return CrsDescriptor(**values)

    def messages(self, descriptor: CrsDescriptor) -> list[str]:
        return [
            issue.message.format(*issue.args)
            for issue in crs_metadata_issues([descriptor])
        ]

    def test_valid_projected_crs_has_no_issues(self) -> None:
        self.assertEqual(
            crs_metadata_issues([self.descriptor()]), []
        )

    def test_deprecated_crs(self) -> None:
        messages = self.messages(self.descriptor(deprecated=True))
        self.assertTrue(
            any("устаревшая" in message for message in messages),
            messages,
        )

    def test_crs_without_authority_code(self) -> None:
        messages = self.messages(self.descriptor(authid=""))
        self.assertTrue(
            any("без кода EPSG" in message for message in messages),
            messages,
        )

    def test_non_metric_units(self) -> None:
        messages = self.messages(
            self.descriptor(units="FeetUSSurvey")
        )
        self.assertTrue(
            any("не метрические" in message for message in messages),
            messages,
        )

    def test_geographic_crs_with_degrees(self) -> None:
        self.assertEqual(
            crs_metadata_issues(
                [
                    self.descriptor(
                        authid="EPSG:4326",
                        description="WGS 84",
                        geographic=True,
                        projected=False,
                        units="Degrees",
                        axis_inverted=True,
                    )
                ]
            ),
            [],
        )

    def test_geographic_crs_with_wrong_units(self) -> None:
        messages = self.messages(
            self.descriptor(
                geographic=True,
                projected=False,
                units="Meters",
            )
        )
        self.assertTrue(
            any("ожидаются градусы" in message for message in messages),
            messages,
        )

    def test_projected_crs_with_inverted_axes(self) -> None:
        messages = self.messages(
            self.descriptor(axis_inverted=True)
        )
        self.assertTrue(
            any("порядок осей" in message for message in messages),
            messages,
        )

    def test_missing_crs_can_be_skipped(self) -> None:
        missing = self.descriptor(valid=False)
        self.assertEqual(
            crs_metadata_issues([missing], include_missing=False),
            [],
        )
        self.assertEqual(
            len(crs_metadata_issues([missing], include_missing=True)),
            1,
        )





class AttributeFillTests(unittest.TestCase):
    def test_complete_layer_has_no_issues(self) -> None:
        layer = LayerFillStats(
            "roads",
            2,
            (
                FieldFillStats("name", 2, 0),
                FieldFillStats("code", 2, 0),
            ),
        )
        self.assertEqual(attribute_fill_issues([layer]), [])

    def test_required_null_and_empty_strings_are_reported(self) -> None:
        layer = LayerFillStats(
            "roads",
            4,
            (
                FieldFillStats("name", 4, 0),
                FieldFillStats("code", 4, 2, required=True),
            ),
        )
        issues = attribute_fill_issues([layer])
        self.assertEqual(len(issues), 3)
        summary = issues[0]
        self.assertFalse(summary.detail_only)
        self.assertIn("code", summary.args[6])
        self.assertIn("{}%", summary.message)
        self.assertEqual(summary.args[1], 75)
        self.assertEqual(
            [issue.detail_only for issue in issues[1:]],
            [True, True],
        )
        self.assertEqual(issues[2].message.count("{}"), 5)

    def test_low_fill_field_is_reported_with_rate(self) -> None:
        layer = LayerFillStats(
            "roads",
            10,
            (
                FieldFillStats("id", 10, 0),
                FieldFillStats("comment", 10, 8),
            ),
        )
        issues = attribute_fill_issues([layer])
        summary = issues[0]
        self.assertIn("comment — 20%", summary.args[5])
        self.assertEqual(summary.args[1], 60)
        self.assertTrue(all(issue.detail_only for issue in issues[1:]))

    def test_almost_empty_layer_is_reported(self) -> None:
        layer = LayerFillStats(
            "empty",
            10,
            (
                FieldFillStats("name", 10, 10),
                FieldFillStats("code", 10, 10, required=True),
            ),
            fully_empty_features=10,
        )
        issues = attribute_fill_issues([layer])
        almost = [
            issue
            for issue in issues
            if "почти пустые атрибуты" in issue.message
        ]
        self.assertEqual(len(almost), 1)
        self.assertEqual(almost[0].args, ("empty", 0, 20, 0, 10, 10, 100))
        self.assertEqual(issues[0].args[5], "name — 0%")
        self.assertEqual(issues[0].args[6], "code")

    def test_many_fully_empty_features_trigger_almost_empty(self) -> None:
        fields = tuple(
            FieldFillStats(f"field_{index}", 100, 95)
            for index in range(20)
        )
        layer = LayerFillStats(
            "sparse",
            100,
            fields,
            fully_empty_features=95,
        )
        issues = attribute_fill_issues([layer])
        almost = [
            issue
            for issue in issues
            if "почти пустые атрибуты" in issue.message
        ]
        self.assertEqual(len(almost), 1)
        self.assertEqual(almost[0].args[3], 5)

    def test_exactly_half_fill_is_not_low(self) -> None:
        layer = LayerFillStats(
            "roads",
            2,
            (
                FieldFillStats("full", 2, 0),
                FieldFillStats("half", 2, 1),
            ),
        )
        self.assertEqual(attribute_fill_issues([layer]), [])

    def test_zero_features_and_no_fields_are_skipped(self) -> None:
        self.assertEqual(
            attribute_fill_issues(
                [
                    LayerFillStats(
                        "empty",
                        0,
                        (FieldFillStats("name", 0, 0),),
                    ),
                    LayerFillStats("no_fields", 10, ()),
                ]
            ),
            [],
        )


class TopologySummaryTests(unittest.TestCase):
    def test_no_issues_produces_no_summary(self) -> None:
        self.assertEqual(
            topology_summary_issues(TopologyStats("roads")), []
        )

    def test_summary_contains_all_counts(self) -> None:
        issues = topology_summary_issues(
            TopologyStats(
                "roads",
                polygon_overlaps=2,
                polygon_gaps=1,
                dangling_lines=3,
                free_ends=4,
                line_intersections=5,
                line_overlaps=6,
            )
        )
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.check, "topology")
        self.assertFalse(issue.detail_only)
        self.assertEqual(
            issue.args,
            ("roads", 2, 1, 3, 4, 5, 6),
        )
        self.assertEqual(issue.location, "Топология")

    def test_only_line_issues_are_reported(self) -> None:
        issues = topology_summary_issues(
            TopologyStats("lines", dangling_lines=1, free_ends=1)
        )
        self.assertEqual(len(issues), 1)


class CoordinateProblemTests(unittest.TestCase):
    def test_valid_geographic_coordinate(self) -> None:
        self.assertIsNone(
            coordinate_problem(39.0, 45.0, geographic=True)
        )

    def test_non_finite_coordinates(self) -> None:
        for x, y in (
            (float("nan"), 0.0),
            (0.0, float("inf")),
            (float("-inf"), float("inf")),
        ):
            with self.subTest(x=x, y=y):
                self.assertEqual(
                    coordinate_problem(x, y, geographic=True),
                    "non_finite",
                )

    def test_excessively_large_coordinate(self) -> None:
        self.assertEqual(
            coordinate_problem(1e12, 0.0, geographic=False),
            "huge",
        )

    def test_swapped_latitude_and_longitude(self) -> None:
        self.assertEqual(
            coordinate_problem(45.0, 120.0, geographic=True),
            "swapped",
        )

    def test_out_of_geographic_range(self) -> None:
        self.assertEqual(
            coordinate_problem(200.0, 45.0, geographic=True),
            "out_of_range",
        )
        self.assertEqual(
            coordinate_problem(45.0, 200.0, geographic=True),
            "out_of_range",
        )

    def test_projected_coordinate_is_not_range_checked_here(self) -> None:
        self.assertIsNone(
            coordinate_problem(
                500000.0, 5000000.0, geographic=False
            )
        )


class PrjFileTests(unittest.TestCase):
    PROJECTED = (
        'PROJCS["WGS 84 / Pseudo-Mercator",'
        'GEOGCS["WGS 84",AUTHORITY["EPSG","4326"]],'
        'AUTHORITY["EPSG","3857"]]'
    )
    GEOGRAPHIC = 'GEOGCS["WGS 84",AUTHORITY["EPSG","4326"]]'

    def descriptor(self, **overrides) -> CrsDescriptor:
        values = {
            "layer": "roads",
            "authid": "EPSG:3857",
            "description": "WGS 84 / Pseudo-Mercator",
            "valid": True,
            "geographic": False,
            "projected": True,
            "deprecated": False,
            "units": "Meters",
            "axis_inverted": False,
        }
        values.update(overrides)
        return CrsDescriptor(**values)

    def issues(self, content, descriptors=()):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {}
            if content is not None:
                prj = root / "roads.prj"
                prj.write_bytes(
                    content.encode("utf-8")
                    if isinstance(content, str)
                    else content
                )
                files["roads.prj"] = prj
            return prj_file_issues(
                geo_file(root / "roads.shp"),
                files,
                list(descriptors),
            )

    def messages(self, content, descriptors=()) -> list:
        return [
            issue.message.format(*issue.args)
            for issue in self.issues(content, descriptors)
        ]

    def test_missing_prj_is_reported(self) -> None:
        messages = self.messages(None)
        self.assertTrue(
            any("Нет файла .prj" in message for message in messages),
            messages,
        )

    def test_empty_prj_is_reported(self) -> None:
        messages = self.messages("")
        self.assertTrue(
            any("пуст" in message for message in messages), messages
        )

    def test_broken_wkt_is_reported(self) -> None:
        messages = self.messages("не WKT")
        self.assertTrue(
            any("корректного WKT" in message for message in messages),
            messages,
        )

    def test_unbalanced_brackets_are_reported(self) -> None:
        messages = self.messages('PROJCS["name"')
        self.assertTrue(
            any("корректного WKT" in message for message in messages),
            messages,
        )

    def test_matching_crs_has_no_issues(self) -> None:
        self.assertEqual(
            self.issues(self.PROJECTED, [self.descriptor()]), []
        )

    def test_type_mismatch_is_reported(self) -> None:
        messages = self.messages(self.GEOGRAPHIC, [self.descriptor()])
        self.assertTrue(
            any("не совпадает с CRS слоя" in message for message in messages),
            messages,
        )

    def test_epsg_mismatch_is_reported(self) -> None:
        messages = self.messages(
            self.GEOGRAPHIC,
            [
                self.descriptor(
                    authid="EPSG:32637",
                    geographic=True,
                    projected=False,
                )
            ],
        )
        self.assertTrue(
            any("EPSG:4326" in message for message in messages), messages
        )

    def test_esri_prj_without_epsg_matches_by_type(self) -> None:
        esri = (
            'PROJCS["WGS_1984_UTM_Zone_37N",'
            'GEOGCS["GCS_WGS_1984",'
            'DATUM["D_WGS_1984",'
            'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
            'PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
            'PROJECTION["Transverse_Mercator"],UNIT["Meter",1.0]]'
        )
        self.assertEqual(
            self.messages(esri, [self.descriptor(authid="EPSG:32637")]),
            [],
        )

    def test_cp1251_wkt_is_readable(self) -> None:
        wkt = 'PROJCS["МГГТ ЦМР",GEOGCS["WGS 84"]]'
        messages = self.messages(wkt.encode("cp1251"))
        self.assertEqual(
            [
                message
                for message in messages
                if "корректного WKT" in message
            ],
            [],
        )

    def test_qpj_is_used_when_prj_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            qpj = root / "roads.qpj"
            qpj.write_text(self.PROJECTED, encoding="utf-8")
            self.assertEqual(
                prj_file_issues(
                    geo_file(root / "roads.shp"),
                    {"roads.qpj": qpj},
                    [self.descriptor()],
                ),
                [],
            )

    def test_sidecar_prj_check_can_be_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shp = SimpleNamespace(
                path=root / "roads.shp",
                extension=".shp",
                category="vector",
            )
            self.assertTrue(
                any(
                    ".prj" in issue.location
                    for issue in metadata_sidecar_issues(shp, {})
                )
            )
            self.assertEqual(
                [
                    issue
                    for issue in metadata_sidecar_issues(
                        shp, {}, include_prj=False, include_cpg=False
                    )
                ],
                [],
            )


class DuplicateGeometryTests(unittest.TestCase):
    def messages(self, entries: list) -> list:
        return [
            issue.message.format(*issue.args)
            for issue in duplicate_geometry_issues("roads", entries)
        ]

    def test_identical_geometries_are_reported(self) -> None:
        messages = self.messages([(1, b"a"), (2, b"a")])
        self.assertTrue(
            any("Дубль геометрии объекта 2 — совпадает с объектом 1" in m
                for m in messages),
            messages,
        )
        self.assertTrue(
            any("дублей по геометрии: 1, групп: 1" in m for m in messages),
            messages,
        )

    def test_unique_geometries_are_not_reported(self) -> None:
        self.assertEqual(
            duplicate_geometry_issues("roads", [(1, b"a"), (2, b"b")]),
            [],
        )

    def test_three_identical_geometries_make_one_group(self) -> None:
        messages = self.messages([(1, b"a"), (2, b"a"), (3, b"a")])
        self.assertTrue(
            any("дублей по геометрии: 2, групп: 1" in m for m in messages),
            messages,
        )

    def test_empty_input_is_ignored(self) -> None:
        self.assertEqual(duplicate_geometry_issues("roads", []), [])

    def test_details_are_limited(self) -> None:
        entries = [(0, b"a")] + [(index, b"a") for index in range(1, 20)]
        issues = duplicate_geometry_issues("roads", entries, max_detail=5)
        details = [issue for issue in issues if issue.detail_only]
        self.assertEqual(len(details), 5)
        self.assertTrue(issues[-1].message.startswith("Слой"))


class FilePathTests(unittest.TestCase):
    def geo_file(self, path: Path):
        return SimpleNamespace(
            path=path, extension=path.suffix.lower(), category="vector"
        )

    def messages(self, path: Path, names=(), files=None, **kwargs):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            entries = {}
            for name in files or ():
                entries[name.casefold()] = root / name
            target = root / path.name
            return [
                issue.message.format(*issue.args)
                for issue in file_path_issues(
                    self.geo_file(target),
                    entries,
                    names=names,
                    **kwargs,
                )
            ]

    def test_long_path_is_reported(self) -> None:
        name = "a" * 250 + ".shp"
        messages = self.messages(Path(name))
        self.assertTrue(
            any("ограничение Windows" in message for message in messages),
            messages,
        )

    def test_short_path_has_no_issues(self) -> None:
        self.assertEqual(self.messages(Path("roads.shp")), [])

    def test_invalid_characters(self) -> None:
        self.assertEqual(invalid_name_characters("a<b>c|d?.shp"), "<>?|")
        self.assertEqual(invalid_name_characters("roads.shp"), "")
        messages = self.messages(Path("a*b.shp"))
        self.assertTrue(
            any("Недопустимые символы" in message for message in messages),
            messages,
        )

    def test_reserved_names(self) -> None:
        self.assertTrue(is_reserved_file_name("CON.shp"))
        self.assertTrue(is_reserved_file_name("lpt9.shp"))
        self.assertFalse(is_reserved_file_name("console.shp"))
        messages = self.messages(Path("nul.shp"))
        self.assertTrue(
            any("зарезервировано" in message for message in messages),
            messages,
        )

    def test_case_collision_is_reported(self) -> None:
        names = ("Roads.shp", "roads.shp")
        messages = self.messages(Path("Roads.shp"), names=names)
        self.assertTrue(
            any("различаются только регистром" in message
                for message in messages),
            messages,
        )

    def test_case_collision_is_reported_once(self) -> None:
        names = ("Roads.shp", "roads.shp")
        self.assertEqual(
            [
                message
                for message in self.messages(Path("roads.shp"), names=names)
                if "различаются только регистром" in message
            ],
            [],
        )

    def test_unique_names_have_no_collision(self) -> None:
        self.assertEqual(
            self.messages(Path("roads.shp"), names=("roads.shp",)),
            [],
        )

    def test_orphan_sidecars_are_detected(self) -> None:
        self.assertEqual(
            orphan_sidecars(
                {
                    "roads.shp": Path("roads.shp"),
                    "roads.dbf": Path("roads.dbf"),
                    "lost.dbf": Path("lost.dbf"),
                    "lost.prj": Path("lost.prj"),
                    "dem.tif": Path("dem.tif"),
                    "dem.tif.aux.xml": Path("dem.tif.aux.xml"),
                    "old.tif.ovr": Path("old.tif.ovr"),
                    "readme.xml": Path("readme.xml"),
                }
            ),
            ["lost.dbf", "lost.prj", "old.tif.ovr"],
        )

    def test_sidecar_forces_primary_names(self) -> None:
        files = {
            "roads.shp": Path("roads.shp"),
            "roads.prj": Path("roads.prj"),
            "dem.tif": Path("dem.tif"),
            "dem.tfw": Path("dem.tfw"),
        }
        self.assertEqual(orphan_sidecars(files), [])

    def test_orphans_are_reported_once_per_folder(self) -> None:
        files = ("roads.shp", "lost.dbf")
        owner = self.messages(
            Path("roads.shp"), files=files, folder_owner=True
        )
        self.assertTrue(
            any("Осиротевший" in message for message in owner), owner
        )
        other = self.messages(Path("roads.shp"), files=files)
        self.assertEqual(
            [m for m in other if "Осиротевший" in m], []
        )


class ReadabilityTests(unittest.TestCase):
    def test_file_level_problems(self) -> None:
        issues = readability_issues(
            [
                ReadabilityProblem("file_missing"),
                ReadabilityProblem("empty_file"),
                ReadabilityProblem("no_layers"),
            ],
            "readability",
        )
        self.assertEqual(
            [issue.message for issue in issues],
            [
                "Файл не найден или недоступен",
                "Файл пуст (0 байт)",
                "QGIS не смог открыть файл: нет доступных слоёв",
            ],
        )
        self.assertTrue(all(issue.check == "readability" for issue in issues))
        self.assertTrue(all(issue.location == "Файл" for issue in issues))

    def test_open_and_read_problems_keep_details(self) -> None:
        issues = readability_issues(
            [
                ReadabilityProblem("open", detail="driver error"),
                ReadabilityProblem(
                    "vector_read",
                    layer="roads",
                    detail="broken DBF",
                ),
                ReadabilityProblem(
                    "raster_read",
                    layer="dem",
                    detail="block error",
                ),
            ],
            "readability",
        )
        self.assertEqual(
            issues[0].args,
            (": driver error",),
        )
        self.assertEqual(issues[1].layer, "roads")
        self.assertEqual(issues[1].args, ("roads", ": broken DBF"))
        self.assertEqual(issues[2].layer, "dem")
        self.assertEqual(issues[2].args, ("dem", ": block error"))
        self.assertEqual(issues[1].location, "Чтение")

    def test_unknown_problem_kind_is_ignored(self) -> None:
        self.assertEqual(
            readability_issues(
                [ReadabilityProblem("unknown")],
                "readability",
            ),
            [],
        )


class DirectoryFilesTests(unittest.TestCase):
    def test_cache_and_lowercase_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "A.SHP").write_bytes(b"x")
            cache = {}
            first = directory_files(root, cache)
            second = directory_files(root, cache)
            self.assertIs(first, second)
            self.assertIn("a.shp", first)


if __name__ == "__main__":
    unittest.main()
