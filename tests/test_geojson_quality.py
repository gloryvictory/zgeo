"""Проверки содержимого GeoJSON."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from zgeo.geojson_quality import (
    MAX_GEOJSON_ISSUES,
    validate_geojson_document,
    validate_geojson_file,
)

CHECK = "geojson_quality"


def _validate(document: object) -> list:
    return validate_geojson_document(document, CHECK)


def _messages(issues: list) -> list:
    return [issue.message for issue in issues if not issue.detail_only]


def _details(issues: list) -> list:
    return [issue.message for issue in issues if issue.detail_only]


class GeoJsonQualityDocumentTests(unittest.TestCase):
    def test_valid_feature_collection(self) -> None:
        issues = _validate(
            {
                "type": "FeatureCollection",
                "bbox": [0, 0, 10, 10],
                "features": [
                    {
                        "type": "Feature",
                        "id": 7,
                        "geometry": {
                            "type": "Point",
                            "coordinates": [1, 2, 3],
                        },
                        "properties": {"name": "A"},
                    },
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [0, 0],
                                    [0, 1],
                                    [1, 1],
                                    [0, 0],
                                ]
                            ],
                        },
                        "properties": None,
                    },
                ],
            }
        )
        self.assertEqual(issues, [])

    def test_valid_empty_collections(self) -> None:
        self.assertEqual(
            _validate({"type": "FeatureCollection", "features": []}),
            [],
        )
        self.assertEqual(
            _validate(
                {"type": "GeometryCollection", "geometries": []}
            ),
            [],
        )

    def test_valid_nested_geometry_collection(self) -> None:
        self.assertEqual(
            _validate(
                {
                    "type": "GeometryCollection",
                    "geometries": [
                        {
                            "type": "GeometryCollection",
                            "geometries": [
                                {
                                    "type": "Point",
                                    "coordinates": [1, 2],
                                }
                            ],
                        }
                    ],
                }
            ),
            [],
        )

    def test_nan_inf_and_non_numeric_coordinates(self) -> None:
        for coordinate in (math.nan, math.inf, -math.inf):
            with self.subTest(coordinate=coordinate):
                issues = _validate(
                    {
                        "type": "Point",
                        "coordinates": [coordinate, 2],
                    }
                )
                self.assertIn("Координата NaN/Inf", _details(issues))
        issues = _validate(
            {"type": "Point", "coordinates": ["1", 2]}
        )
        self.assertIn(
            "Координата должна быть числом: {}",
            _details(issues),
        )

    def test_huge_integer_coordinate_is_reported_not_crashing(self) -> None:
        issues = _validate(
            {"type": "Point", "coordinates": [10**400, 0]}
        )
        self.assertIn(
            "Долгота вне диапазона [-180, 180]: {}",
            _details(issues),
        )

    def test_coordinate_ranges_and_swapped_axes(self) -> None:
        longitude = _validate(
            {"type": "Point", "coordinates": [200, 0]}
        )
        self.assertIn(
            "Долгота вне диапазона [-180, 180]: {}",
            _details(longitude),
        )
        latitude = _validate(
            {"type": "Point", "coordinates": [0, 95]}
        )
        self.assertIn(
            "Похоже на перепутанные широту и долготу",
            _details(latitude),
        )
        invalid_latitude = _validate(
            {"type": "Point", "coordinates": [100, 95]}
        )
        self.assertIn(
            "Широта вне диапазона [-90, 90]: {}",
            _details(invalid_latitude),
        )

    def test_position_must_have_two_numbers(self) -> None:
        issues = _validate(
            {"type": "Point", "coordinates": [1]}
        )
        self.assertIn(
            "Позиция должна содержать не менее двух чисел",
            _details(issues),
        )
        issues = _validate(
            {"type": "Point", "coordinates": "1,2"}
        )
        self.assertIn(
            "Позиция должна быть массивом чисел",
            _details(issues),
        )

    def test_linestring_minimum_length(self) -> None:
        issues = _validate(
            {
                "type": "LineString",
                "coordinates": [[0, 0]],
            }
        )
        self.assertIn(
            "LineString должен содержать не менее 2 точек",
            _details(issues),
        )

    def test_ring_must_be_closed_and_have_four_points(self) -> None:
        unclosed = _validate(
            {
                "type": "Polygon",
                "coordinates": [
                    [[0, 0], [0, 1], [1, 1], [1, 0]]
                ],
            }
        )
        self.assertIn(
            "Кольцо не замкнуто: первая и последняя точки не совпадают",
            _details(unclosed),
        )

        short = _validate(
            {
                "type": "Polygon",
                "coordinates": [
                    [[0, 0], [0, 1], [0, 0]]
                ],
            }
        )
        self.assertIn(
            "Кольцо должно содержать не менее 4 точек",
            _details(short),
        )

    def test_polygon_must_have_ring(self) -> None:
        issues = _validate(
            {"type": "Polygon", "coordinates": []}
        )
        self.assertIn(
            "Полигон должен содержать хотя бы одно кольцо",
            _details(issues),
        )

    def test_multipolygon_structure(self) -> None:
        issues = _validate(
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [[0, 0], [0, 1], [1, 1], [0, 0]]
                    ]
                ],
            }
        )
        self.assertEqual(issues, [])

        issues = _validate(
            {
                "type": "MultiPolygon",
                "coordinates": ["not a polygon"],
            }
        )
        self.assertIn(
            "Полигон в MultiPolygon должен быть массивом колец",
            _details(issues),
        )

    def test_bbox_format_and_order(self) -> None:
        wrong_length = _validate(
            {
                "type": "Point",
                "coordinates": [1, 2],
                "bbox": [0, 0, 10],
            }
        )
        self.assertIn(
            "Поле «bbox» должно содержать 4 или 6 чисел",
            _details(wrong_length),
        )

        wrong_order = _validate(
            {
                "type": "Point",
                "coordinates": [1, 2],
                "bbox": [10, 0, 0, 10],
            }
        )
        self.assertIn(
            "bbox: минимум больше максимума по оси {}",
            _details(wrong_order),
        )

        non_finite = _validate(
            {
                "type": "Point",
                "coordinates": [1, 2],
                "bbox": [0, 0, math.inf, 10],
            }
        )
        self.assertIn(
            "Элемент bbox не должен быть NaN/Inf",
            _details(non_finite),
        )

    def test_feature_structure(self) -> None:
        missing_properties = _validate(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [1, 2],
                },
            }
        )
        self.assertIn(
            "Отсутствует обязательное поле «properties»",
            _details(missing_properties),
        )

        wrong_geometry = _validate(
            {
                "type": "Feature",
                "geometry": [],
                "properties": {},
            }
        )
        self.assertIn(
            "Поле «geometry» должно быть объектом или null",
            _details(wrong_geometry),
        )

        wrong_id = _validate(
            {
                "type": "Feature",
                "geometry": None,
                "properties": {},
                "id": True,
            }
        )
        self.assertIn(
            "Поле «id» должно быть строкой или числом",
            _details(wrong_id),
        )

    def test_feature_collection_structure(self) -> None:
        missing_features = _validate({"type": "FeatureCollection"})
        self.assertIn(
            "Отсутствует обязательное поле «features»",
            _details(missing_features),
        )

        wrong_features = _validate(
            {"type": "FeatureCollection", "features": {}}
        )
        self.assertIn(
            "Поле «features» должно быть массивом",
            _details(wrong_features),
        )

        wrong_child = _validate(
            {
                "type": "FeatureCollection",
                "features": [{"type": "Point", "coordinates": [1, 2]}],
            }
        )
        self.assertIn(
            "Тип объекта Feature должен быть «Feature»: {}",
            _details(wrong_child),
        )

    def test_geometry_collection_structure(self) -> None:
        missing_geometries = _validate(
            {"type": "GeometryCollection"}
        )
        self.assertIn(
            "Отсутствует обязательное поле «geometries»",
            _details(missing_geometries),
        )

        wrong_geometries = _validate(
            {"type": "GeometryCollection", "geometries": {}}
        )
        self.assertIn(
            "Поле «geometries» должно быть массивом",
            _details(wrong_geometries),
        )

        wrong_child = _validate(
            {
                "type": "GeometryCollection",
                "geometries": ["Point"],
            }
        )
        self.assertIn(
            "Элемент GeometryCollection должен быть объектом геометрии",
            _details(wrong_child),
        )

    def test_unknown_and_invalid_types(self) -> None:
        self.assertIn(
            "Неизвестный тип GeoJSON: {}",
            _details(_validate({"type": "Object"})),
        )
        self.assertIn(
            "Отсутствует или неверен тип GeoJSON: {}",
            _details(_validate({"name": "value"})),
        )
        self.assertIn(
            "Корень GeoJSON должен быть объектом",
            _details(_validate([])),
        )

    def test_geometry_with_unknown_type_and_missing_coordinates(
        self,
    ) -> None:
        unknown = _validate(
            {
                "type": "Feature",
                "geometry": {"type": "Circle"},
                "properties": {},
            }
        )
        self.assertIn(
            "Неизвестный тип геометрии: {}",
            _details(unknown),
        )

        missing = _validate(
            {
                "type": "Feature",
                "geometry": {"type": "Point"},
                "properties": {},
            }
        )
        self.assertIn(
            "Отсутствует обязательное поле «coordinates»",
            _details(missing),
        )

    def test_summary_has_counts_and_details_are_hidden_from_tooltip(
        self,
    ) -> None:
        issues = _validate(
            {
                "type": "Polygon",
                "coordinates": [
                    [[0, 0], [0, 1], [1, 1], [1, 0]]
                ],
            }
        )
        self.assertEqual(
            _messages(issues),
            [
                "Ошибок GeoJSON: {} (координаты: {}, кольца: {}, "
                "bbox: {}, структура: {})"
            ],
        )
        self.assertEqual(issues[0].args, (1, 0, 1, 0, 0))
        self.assertTrue(issues[1].detail_only)

    def test_issue_limit(self) -> None:
        positions = []
        for index in range(MAX_GEOJSON_ISSUES + 1):
            positions.append([200 + index, 0])
        issues = _validate(
            {"type": "LineString", "coordinates": positions}
        )
        self.assertEqual(issues[0].args[0], MAX_GEOJSON_ISSUES + 1)
        self.assertEqual(
            sum(1 for issue in issues if issue.detail_only),
            MAX_GEOJSON_ISSUES + 1,
        )
        self.assertEqual(
            issues[-1].message,
            "Дополнительные ошибки не показаны (лимит {}).",
        )
        self.assertEqual(issues[-1].args, (MAX_GEOJSON_ISSUES,))


class GeoJsonQualityFileTests(unittest.TestCase):
    def _write(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".geojson", delete=False, encoding="utf-8"
        )
        handle.write(content)
        handle.close()
        path = Path(handle.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_valid_file(self) -> None:
        path = self._write(
            json.dumps(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            "properties": {},
                        }
                    ],
                }
            )
        )
        self.assertEqual(validate_geojson_file(path, CHECK), [])

    def test_invalid_json_file(self) -> None:
        path = self._write('{"type": "FeatureCollection",')
        issues = validate_geojson_file(path, CHECK)
        self.assertEqual(
            issues[0].message, "Не удалось прочитать GeoJSON: {}"
        )
        self.assertFalse(issues[0].detail_only)

    def test_missing_file(self) -> None:
        issues = validate_geojson_file(
            Path(tempfile.gettempdir()) / "zgeo-missing.geojson",
            CHECK,
        )
        self.assertEqual(
            issues[0].message, "Не удалось прочитать GeoJSON: {}"
        )


if __name__ == "__main__":
    unittest.main()
