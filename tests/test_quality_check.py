"""Проверки качества полей, набора данных и слоёв."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from zgeo.quality_check import (
    CrsDescriptor,
    completeness_issues,
    coordinate_problem,
    crs_issues,
    crs_metadata_issues,
    dbf_encoding_issues,
    directory_files,
    empty_layer_issues,
    field_name_issues,
    is_known_encoding,
    metadata_sidecar_issues,
    truncated_duplicate_issues,
)


def geo_file(path: Path):
    return SimpleNamespace(path=path, extension=path.suffix.lower())


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


class EmptyLayerTests(unittest.TestCase):
    def test_empty_file(self) -> None:
        issues = empty_layer_issues([("roads", 0)])
        messages = [issue.message for issue in issues]
        self.assertIn("Файл не содержит объектов", messages)
        self.assertIn("Слой «{}» не содержит объектов", messages)

    def test_one_empty_layer(self) -> None:
        issues = empty_layer_issues([("one", 0), ("two", 10)])
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].args, ("one",))

    def test_non_empty_layers(self) -> None:
        self.assertEqual(empty_layer_issues([("one", 5)]), [])

    def test_unknown_count_is_not_empty(self) -> None:
        self.assertEqual(empty_layer_issues([("one", -1)]), [])


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
