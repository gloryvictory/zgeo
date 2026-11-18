"""Проверки качества полей, набора данных и слоёв."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from zgeo.quality_check import (
    CrsDescriptor,
    FieldFillStats,
    LayerFillStats,
    TopologyStats,
    attribute_fill_issues,
    completeness_issues,
    coordinate_problem,
    crs_issues,
    crs_metadata_issues,
    dbf_encoding_issues,
    directory_files,
    duplicate_geometry_issues,
    file_path_issues,
    invalid_name_characters,
    is_reserved_file_name,
    orphan_sidecars,
    empty_layer_issues,
    field_name_issues,
    file_path_issues,
    invalid_name_characters,
    is_known_encoding,
    is_reserved_file_name,
    orphan_sidecars,
    metadata_sidecar_issues,
    prj_file_issues,
    topology_summary_issues,
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
