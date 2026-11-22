import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from zgeo.content_check import (
    CONTENT_ARCHIVE,
    CONTENT_BINARY,
    CONTENT_EXECUTABLE,
    CONTENT_FLATGEOBUF,
    CONTENT_IMAGE,
    CONTENT_JSON,
    CONTENT_NETCDF,
    CONTENT_OLE2,
    CONTENT_PARQUET,
    CONTENT_SHAPEFILE,
    CONTENT_SQLITE,
    CONTENT_TEXT,
    CONTENT_TIFF,
    CONTENT_XML,
    CONTENT_ZIP,
    content_kind_label,
    content_mismatch_issues,
    detect_content_kind,
    inspect_content_mismatch,
)


def write(folder: Path, name: str, data: bytes) -> Path:
    path = folder / name
    path.write_bytes(data)
    return path


def geo_file(path: Path) -> SimpleNamespace:
    return SimpleNamespace(path=path, extension=path.suffix.lower())


class DetectContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="zgeo-content-"))

    def test_signatures_are_detected(self) -> None:
        cases = {
            "a.gpkg": (b"SQLite format 3\x00rest", CONTENT_SQLITE),
            "a.shp": (b"\x00\x00\x27\x0afile header", CONTENT_SHAPEFILE),
            "a.tif": (b"II*\x00data", CONTENT_TIFF),
            "a.kmz": (b"PK\x03\x04data", CONTENT_ZIP),
            "a.xls": (b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1data", CONTENT_OLE2),
            "a.parquet": (b"PAR1data", CONTENT_PARQUET),
            "a.fgb": (b"fgb\x03data", CONTENT_FLATGEOBUF),
            "a.nc": (b"CDF\x01data", CONTENT_NETCDF),
            "a.png": (b"\x89PNG\r\n\x1a\ndata", CONTENT_IMAGE),
            "a.gz": (b"\x1f\x8bdata", CONTENT_ARCHIVE),
            "a.exe": (b"MZdata", CONTENT_EXECUTABLE),
        }
        for name, (data, expected) in cases.items():
            with self.subTest(name=name):
                path = write(self.folder, name, data)
                self.assertEqual(detect_content_kind(path), expected)

    def test_text_kinds_are_detected(self) -> None:
        json_path = write(self.folder, "a.json", b'{"type": "Feature"}')
        xml_path = write(self.folder, "a.kml", b"<?xml version='1.0'?>")
        text_path = write(self.folder, "a.csv", b"name;code")
        binary_path = write(self.folder, "a.bin", b"\x00\x01\x02")
        self.assertEqual(detect_content_kind(json_path), CONTENT_JSON)
        self.assertEqual(detect_content_kind(xml_path), CONTENT_XML)
        self.assertEqual(detect_content_kind(text_path), CONTENT_TEXT)
        self.assertEqual(detect_content_kind(binary_path), CONTENT_BINARY)

    def test_empty_and_missing_files_have_no_kind(self) -> None:
        empty = write(self.folder, "a.shp", b"")
        self.assertEqual(detect_content_kind(empty), "")
        self.assertEqual(
            detect_content_kind(self.folder / "missing.shp"), ""
        )


class MismatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = Path(tempfile.mkdtemp(prefix="zgeo-mismatch-"))

    def test_matching_content_has_no_issues(self) -> None:
        path = write(self.folder, "a.gpkg", b"SQLite format 3\x00data")
        issues, applicable = inspect_content_mismatch(
            geo_file(path), "content_mismatch"
        )
        self.assertTrue(applicable)
        self.assertEqual(issues, [])

    def test_shapefile_holding_a_zip_is_reported(self) -> None:
        path = write(self.folder, "roads.shp", b"PK\x03\x04data")
        issues, applicable = inspect_content_mismatch(
            geo_file(path), "content_mismatch"
        )
        self.assertTrue(applicable)
        self.assertEqual(len(issues), 1)
        issue = issues[0]
        self.assertEqual(issue.check, "content_mismatch")
        rendered = issue.message.format(*issue.args)
        self.assertIn("roads.shp", rendered)
        self.assertIn(".shp", rendered)

    def test_gpkg_without_sqlite_header_is_reported(self) -> None:
        path = write(self.folder, "data.gpkg", b"just some text")
        issues, _applicable = inspect_content_mismatch(
            geo_file(path), "content_mismatch"
        )
        self.assertEqual(len(issues), 1)

    def test_empty_and_unknown_files_are_not_applicable(self) -> None:
        empty = write(self.folder, "a.shp", b"")
        issues, applicable = inspect_content_mismatch(
            geo_file(empty), "content_mismatch"
        )
        self.assertEqual(issues, [])
        self.assertFalse(applicable)

        unknown = write(self.folder, "a.docx", b"PK\x03\x04")
        issues, applicable = inspect_content_mismatch(
            geo_file(unknown), "content_mismatch"
        )
        self.assertEqual(issues, [])
        self.assertFalse(applicable)

    def test_missing_file_is_not_applicable(self) -> None:
        issues, applicable = inspect_content_mismatch(
            geo_file(self.folder / "missing.gpkg"), "content_mismatch"
        )
        self.assertEqual(issues, [])
        self.assertFalse(applicable)

    def test_issue_label_is_localized(self) -> None:
        path = write(self.folder, "a.tif", b"PK\x03\x04")
        issues = content_mismatch_issues(geo_file(path), CONTENT_ZIP)
        rendered = issues[0].message.format(*issues[0].args)
        self.assertIn(content_kind_label(CONTENT_ZIP), rendered)


if __name__ == "__main__":
    unittest.main()
