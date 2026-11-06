from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zgeo.dataset_size import measure_geo_file, refine_geo_files
from zgeo.scanner import VECTOR, FormatInfo, GeoFile


class DatasetSizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, relative_path: str, content: bytes = b"data") -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def geo_file(self, path: Path, name: str = "Shapefile") -> GeoFile:
        return GeoFile(
            path=path,
            relative_path=path.relative_to(self.root),
            format=FormatInfo(name, VECTOR),
            size=path.stat().st_size,
        )

    def test_shapefile_includes_all_sidecars(self) -> None:
        path = self.write("roads.shp", b"a" * 10)
        self.write("roads.dbf", b"b" * 20)
        self.write("roads.shx", b"c" * 5)
        self.write("roads.prj", b"d" * 3)
        self.write("roads.cpg", b"e" * 2)
        self.write("roads.shp.xml", b"f" * 4)

        detail = measure_geo_file(self.geo_file(path))

        self.assertEqual(detail.primary_size, 10)
        self.assertEqual(detail.sidecar_size, 34)
        self.assertEqual(detail.total_size, 44)
        self.assertEqual(
            {item.name for item in detail.sidecars},
            {"roads.dbf", "roads.shx", "roads.prj", "roads.cpg", "roads.shp.xml"},
        )

    def test_mif_includes_mid(self) -> None:
        path = self.write("layer.mif", b"a" * 7)
        self.write("layer.mid", b"b" * 11)

        detail = measure_geo_file(self.geo_file(path, "MapInfo MIF"))

        self.assertEqual(detail.primary_size, 7)
        self.assertEqual(detail.sidecar_size, 11)
        self.assertEqual(detail.total_size, 18)
        self.assertEqual([item.name for item in detail.sidecars], ["layer.mid"])

    def test_tab_includes_mapinfo_sidecars(self) -> None:
        path = self.write("layer.tab", b"a" * 3)
        self.write("layer.dat", b"b" * 5)
        self.write("layer.map", b"c" * 7)
        self.write("layer.id", b"d" * 11)
        self.write("layer.ind", b"e" * 13)

        detail = measure_geo_file(self.geo_file(path, "MapInfo TAB"))

        self.assertEqual(detail.total_size, 39)

    def test_raster_includes_appended_and_stem_sidecars(self) -> None:
        path = self.write("dem.tif", b"a" * 20)
        self.write("dem.tif.aux.xml", b"b" * 5)
        self.write("dem.tif.ovr", b"c" * 7)
        self.write("dem.tfw", b"d" * 2)
        self.write("dem.prj", b"e" * 3)

        detail = measure_geo_file(self.geo_file(path, "GeoTIFF / TIFF"))

        self.assertEqual(detail.total_size, 37)

    def test_sidecar_matching_is_case_insensitive(self) -> None:
        path = self.write("ROADS.SHP", b"a" * 10)
        self.write("ROADS.DBF", b"b" * 20)
        self.write("ROADS.ShX", b"c" * 5)

        detail = measure_geo_file(self.geo_file(path))

        self.assertEqual(detail.total_size, 35)
        self.assertEqual(
            {item.name for item in detail.sidecars},
            {"ROADS.DBF", "ROADS.ShX"},
        )

    def test_missing_sidecars_keeps_primary_size(self) -> None:
        path = self.write("only.shp", b"a" * 9)

        detail = measure_geo_file(self.geo_file(path))

        self.assertEqual(detail.primary_size, 9)
        self.assertEqual(detail.sidecar_size, 0)
        self.assertEqual(detail.sidecars, ())

    def test_unrelated_files_are_not_counted(self) -> None:
        path = self.write("roads.shp", b"a" * 10)
        self.write("roads.dbf.bak", b"b" * 100)
        self.write("other.dbf", b"c" * 100)

        detail = measure_geo_file(self.geo_file(path))

        self.assertEqual(detail.total_size, 10)

    def test_refine_returns_updated_copies_and_reports_progress(self) -> None:
        shape = self.write("roads.shp", b"a" * 10)
        self.write("roads.dbf", b"b" * 20)
        gpkg = self.write("city.gpkg", b"c" * 30)

        original = [
            self.geo_file(shape),
            self.geo_file(gpkg, "GeoPackage"),
        ]
        seen = []
        refined = refine_geo_files(
            original,
            progress_callback=lambda current, total, path: seen.append(
                (current, total, path.name)
            ),
        )

        self.assertEqual([item.size for item in refined], [30, 30])
        self.assertEqual([item.size for item in original], [10, 30])
        self.assertEqual(
            seen,
            [(1, 2, "roads.shp"), (2, 2, "city.gpkg")],
        )

    def test_refine_can_be_cancelled(self) -> None:
        first = self.write("a.shp", b"a")
        second = self.write("b.shp", b"b")

        refined = refine_geo_files(
            [self.geo_file(first), self.geo_file(second)],
            should_cancel=lambda: True,
        )

        self.assertEqual(refined, [])


if __name__ == "__main__":
    unittest.main()
