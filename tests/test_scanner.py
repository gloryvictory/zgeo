from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zgeo.scanner import (
    DEFAULT_DISABLED_FORMATS,
    FORMATS,
    RASTER,
    TABLE,
    VECTOR,
    get_format,
    get_format_groups,
    scan_folder,
)


class ScanFolderTests(unittest.TestCase):
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

    def test_recursive_scan_finds_supported_files_only(self) -> None:
        self.write("roads.SHP", b"12345")
        self.write("roads.dbf")
        self.write("roads.shp.xml")
        self.write("tables/attributes.csv")
        self.write("nested/city.gpkg", b"123")
        self.write("nested/rasters/dem.tif", b"1234567")
        self.write("nested/readme.txt")
        self.write(".hidden/hidden.geojson")

        files = scan_folder(self.root)

        self.assertEqual(
            [item.relative_posix for item in files],
            [
                ".hidden/hidden.geojson",
                "nested/city.gpkg",
                "nested/rasters/dem.tif",
                "roads.SHP",
                "tables/attributes.csv",
            ],
        )
        self.assertEqual(files[3].size, 5)
        self.assertEqual(files[3].format.category, VECTOR)
        self.assertEqual(files[2].format.category, RASTER)
        self.assertEqual(files[4].format.category, TABLE)

    def test_non_recursive_scan_ignores_nested_folders(self) -> None:
        self.write("roads.shp")
        self.write("city.gpkg", b"123")
        self.write("nested/deep/dem.tif")

        files = scan_folder(self.root, recursive=False)

        self.assertEqual(
            [item.relative_posix for item in files],
            ["city.gpkg", "roads.shp"],
        )

    def test_extension_matching_is_case_insensitive(self) -> None:
        self.write("UPPER.GPKG")
        self.write("mixed.GeoJSON")

        files = scan_folder(self.root)

        self.assertEqual(
            [item.extension for item in files], [".geojson", ".gpkg"]
        )

    def test_empty_folder_returns_empty_list(self) -> None:
        self.assertEqual(scan_folder(self.root), [])

    def test_progress_callback_reports_files_and_found_count(self) -> None:
        self.write("roads.gpkg")
        self.write("notes.txt")
        self.write("dem.tif")

        seen = []
        files = scan_folder(
            self.root,
            progress_callback=lambda path, count: seen.append(
                (path.name, count)
            ),
        )

        self.assertEqual(len(seen), 2)
        self.assertEqual(
            {name for name, _count in seen},
            {"roads.gpkg", "dem.tif"},
        )
        self.assertEqual([count for _name, count in seen], [1, 2])
        self.assertEqual(seen[-1][1], len(files))
        self.assertEqual(len(files), 2)

    def test_scan_can_be_cancelled_with_partial_result(self) -> None:
        for index in range(10):
            self.write("layer_{}.gpkg".format(index))

        seen = []
        files = scan_folder(
            self.root,
            progress_callback=lambda path, count: seen.append(path),
            should_cancel=lambda: len(seen) >= 3,
        )

        self.assertEqual(len(seen), 3)
        self.assertEqual(len(files), 3)

    def test_scan_can_be_cancelled_before_start(self) -> None:
        self.write("roads.gpkg")

        files = scan_folder(self.root, should_cancel=lambda: True)

        self.assertEqual(files, [])

    def test_enabled_formats_filter_scan(self) -> None:
        self.write("keep.gpkg")
        self.write("skip.xlsx")
        self.write("keep.tif")
        self.write("skip.csv")

        files = scan_folder(
            self.root,
            enabled_formats={"GeoPackage", "GeoTIFF / TIFF"},
        )

        self.assertEqual(
            [item.relative_posix for item in files],
            ["keep.gpkg", "keep.tif"],
        )

    def test_empty_enabled_formats_finds_nothing(self) -> None:
        self.write("roads.gpkg")

        self.assertEqual(
            scan_folder(self.root, enabled_formats=set()), []
        )

    def test_excel_is_disabled_by_default(self) -> None:
        self.write("roads.gpkg")
        self.write("table.xlsx")

        enabled = {
            info.name
            for info in FORMATS.values()
            if info.name not in DEFAULT_DISABLED_FORMATS
        }
        files = scan_folder(
            self.root, enabled_formats=enabled
        )

        self.assertEqual(
            [item.relative_posix for item in files],
            ["roads.gpkg"],
        )

    def test_missing_folder_raises(self) -> None:
        with self.assertRaises(NotADirectoryError):
            scan_folder(self.root / "does-not-exist")

    def test_get_format(self) -> None:
        self.assertIsNotNone(get_format(Path("layer.TIF")))
        self.assertIsNone(get_format(Path("notes.docx")))

    def test_format_groups_and_defaults(self) -> None:
        groups = {
            group.name: group for group in get_format_groups()
        }

        self.assertEqual(
            set(groups),
            {info.name for info in FORMATS.values()},
        )
        self.assertEqual(
            groups["Excel"].extensions, (".xls", ".xlsx")
        )
        self.assertIn("Excel", DEFAULT_DISABLED_FORMATS)


if __name__ == "__main__":
    unittest.main()
