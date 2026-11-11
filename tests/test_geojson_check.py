"""Проверки распознавания GeoJSON по полю type."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from zgeo.geojson_check import (
    JSON_EXTENSIONS,
    check_json_file,
    is_geojson_document,
)


class GeoJsonDocumentTests(unittest.TestCase):
    def test_feature_collection_with_features(self) -> None:
        self.assertTrue(
            is_geojson_document(
                {
                    "type": "FeatureCollection",
                    "features": [
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": "Point",
                                "coordinates": [1, 2],
                            },
                            "properties": {"name": "A"},
                        }
                    ],
                }
            )
        )

    def test_empty_feature_collection(self) -> None:
        self.assertTrue(
            is_geojson_document(
                {"type": "FeatureCollection", "features": []}
            )
        )

    def test_feature_and_geometry_types(self) -> None:
        for geometry_type in (
            "Point",
            "MultiPoint",
            "LineString",
            "MultiLineString",
            "Polygon",
            "MultiPolygon",
        ):
            with self.subTest(geometry_type=geometry_type):
                self.assertTrue(
                    is_geojson_document(
                        {"type": geometry_type, "coordinates": []}
                    )
                )
                self.assertTrue(
                    is_geojson_document(
                        {
                            "type": "Feature",
                            "geometry": {
                                "type": geometry_type,
                                "coordinates": [],
                            },
                            "properties": None,
                        }
                    )
                )

    def test_feature_with_null_geometry(self) -> None:
        self.assertTrue(
            is_geojson_document(
                {"type": "Feature", "geometry": None, "properties": {}}
            )
        )

    def test_geometry_collection(self) -> None:
        self.assertTrue(
            is_geojson_document(
                {
                    "type": "GeometryCollection",
                    "geometries": [
                        {"type": "Point", "coordinates": [1, 2]},
                        {"type": "Polygon", "coordinates": []},
                    ],
                }
            )
        )

    def test_plain_json_object_is_rejected(self) -> None:
        self.assertFalse(is_geojson_document({"name": "value"}))
        self.assertFalse(is_geojson_document({}))

    def test_unknown_type_is_rejected(self) -> None:
        self.assertFalse(is_geojson_document({"type": "Object"}))

    def test_non_object_root_is_rejected(self) -> None:
        for value in ([], [{"type": "Point"}], "type", 42, None):
            with self.subTest(value=value):
                self.assertFalse(is_geojson_document(value))

    def test_feature_collection_with_wrong_features_is_rejected(self) -> None:
        self.assertFalse(
            is_geojson_document(
                {"type": "FeatureCollection", "features": {"type": "Feature"}}
            )
        )
        self.assertFalse(
            is_geojson_document(
                {
                    "type": "FeatureCollection",
                    "features": [{"type": "Point", "coordinates": []}],
                }
            )
        )

    def test_feature_with_wrong_parts_is_rejected(self) -> None:
        self.assertFalse(
            is_geojson_document(
                {"type": "Feature", "geometry": {"type": "Feature"}}
            )
        )
        self.assertFalse(
            is_geojson_document(
                {"type": "Feature", "geometry": None, "properties": []}
            )
        )

    def test_geometry_collection_with_wrong_child_is_rejected(self) -> None:
        self.assertFalse(
            is_geojson_document(
                {
                    "type": "GeometryCollection",
                    "geometries": [{"type": "Feature"}],
                }
            )
        )


class GeoJsonFileTests(unittest.TestCase):
    def _write(self, content: str) -> Path:
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False, encoding="utf-8"
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
        result = check_json_file(path)
        self.assertTrue(result.is_geojson)
        self.assertEqual(result.document_type, "FeatureCollection")
        self.assertEqual(result.error, "")

    def test_file_with_utf8_bom(self) -> None:
        path = self._write("")
        path.write_bytes(
            b"\xef\xbb\xbf"
            + b'{"type": "Point", "coordinates": [1, 2]}'
        )
        result = check_json_file(path)
        self.assertTrue(result.is_geojson)
        self.assertEqual(result.document_type, "Point")

    def test_invalid_json_is_rejected(self) -> None:
        path = self._write('{"type": "FeatureCollection",')
        result = check_json_file(path)
        self.assertFalse(result.is_geojson)
        self.assertNotEqual(result.error, "")

    def test_plain_json_is_rejected(self) -> None:
        path = self._write('{"name": "value"}')
        result = check_json_file(path)
        self.assertFalse(result.is_geojson)
        self.assertEqual(result.document_type, "")

    def test_missing_file_is_rejected(self) -> None:
        result = check_json_file(
            Path(tempfile.gettempdir()) / "zgeo-missing-file.json"
        )
        self.assertFalse(result.is_geojson)
        self.assertNotEqual(result.error, "")

    def test_json_extensions(self) -> None:
        self.assertEqual(JSON_EXTENSIONS, {".json", ".geojson"})


if __name__ == "__main__":
    unittest.main()
