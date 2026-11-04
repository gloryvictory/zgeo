from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zgeo.scanner import RASTER, TABLE, VECTOR, get_format, scan_folder


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

    def test_missing_folder_raises(self) -> None:
        with self.assertRaises(NotADirectoryError):
            scan_folder(self.root / "does-not-exist")

    def test_get_format(self) -> None:
        self.assertIsNotNone(get_format(Path("layer.TIF")))
        self.assertIsNone(get_format(Path("notes.docx")))


if __name__ == "__main__":
    unittest.main()
