"""Проверки копирования выбранных наборов данных."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from zgeo.copy_files import CHUNK_SIZE, build_copy_plan, copy_plan
from zgeo.scanner import VECTOR, FormatInfo, GeoFile


class CopyFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "source"
        self.destination = self.root / "destination"
        self.source.mkdir()
        self.destination.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(
        self,
        path: Path,
        content: bytes = b"data",
    ) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def temporary_files(self) -> list[Path]:
        return [
            path
            for path in self.destination.iterdir()
            if ".zgeo-copy-" in path.name
        ]

    def geo_file(self, path: Path) -> GeoFile:
        return GeoFile(
            path=path,
            relative_path=path.relative_to(self.source),
            format=FormatInfo("Shapefile", VECTOR),
            size=path.stat().st_size,
        )

    def shapefile(self, folder: Path = None) -> GeoFile:
        folder = folder or self.source
        path = self.write(folder / "roads.shp", b"shp")
        self.write(folder / "roads.shx", b"shx")
        self.write(folder / "roads.dbf", b"dbf")
        self.write(folder / "roads.prj", b"prj")
        self.write(folder / "roads.cpg", b"cpg")
        return GeoFile(
            path=path,
            relative_path=path.relative_to(self.source),
            format=FormatInfo("Shapefile", VECTOR),
            size=path.stat().st_size,
        )

    def test_plan_includes_sidecars_and_total_size(self) -> None:
        geo_file = self.shapefile()

        plan = build_copy_plan([geo_file], self.destination)

        self.assertEqual(plan.items[0].source, geo_file.path)
        self.assertEqual(
            {item.source.name for item in plan.items},
            {
                "roads.shp",
                "roads.shx",
                "roads.dbf",
                "roads.prj",
                "roads.cpg",
            },
        )
        self.assertEqual(
            plan.total_size,
            sum(item.size for item in plan.items),
        )
        self.assertEqual(plan.duplicate_names, ())
        self.assertEqual(plan.skipped_same, ())

    def test_copy_plan_copies_files_and_reports_progress(self) -> None:
        geo_file = self.shapefile()
        plan = build_copy_plan([geo_file], self.destination)
        updates = []

        result = copy_plan(
            plan,
            progress_callback=lambda done, total, path: updates.append(
                (done, total)
            ),
        )

        self.assertFalse(result.cancelled)
        self.assertEqual(result.errors, ())
        self.assertEqual(len(result.copied), len(plan.items))
        self.assertEqual(
            (self.destination / "roads.shp").read_bytes(),
            b"shp",
        )
        self.assertEqual(
            (self.destination / "roads.dbf").read_bytes(),
            b"dbf",
        )
        self.assertEqual(
            updates[-1],
            (plan.total_size, plan.total_size),
        )
        self.assertEqual(self.temporary_files(), [])

    def test_copy_plan_replaces_existing_file(self) -> None:
        geo_file = self.shapefile()
        target = self.destination / "roads.shp"
        target.write_bytes(b"old")

        result = copy_plan(build_copy_plan([geo_file], self.destination))

        self.assertEqual(result.errors, ())
        self.assertEqual(target.read_bytes(), b"shp")

    def test_cancel_removes_partial_file(self) -> None:
        path = self.write(
            self.source / "roads.shp",
            b"x" * (CHUNK_SIZE + 10),
        )
        geo_file = self.geo_file(path)
        plan = build_copy_plan([geo_file], self.destination)
        cancelled = [False]

        def on_progress(done: int, total: int, source: Path) -> None:
            cancelled[0] = True

        result = copy_plan(
            plan,
            progress_callback=on_progress,
            should_cancel=lambda: cancelled[0],
        )

        self.assertTrue(result.cancelled)
        self.assertEqual(result.copied, ())
        self.assertFalse((self.destination / "roads.shp").exists())
        self.assertEqual(self.temporary_files(), [])

    def test_cancel_keeps_existing_destination_file(self) -> None:
        path = self.write(
            self.source / "roads.shp",
            b"x" * (CHUNK_SIZE + 10),
        )
        geo_file = self.geo_file(path)
        target = self.destination / "roads.shp"
        target.write_bytes(b"old")
        cancelled = [False]

        def on_progress(done: int, total: int, source: Path) -> None:
            cancelled[0] = True

        result = copy_plan(
            build_copy_plan([geo_file], self.destination),
            progress_callback=on_progress,
            should_cancel=lambda: cancelled[0],
        )

        self.assertTrue(result.cancelled)
        self.assertEqual(target.read_bytes(), b"old")
        self.assertEqual(self.temporary_files(), [])

    def test_duplicate_destination_names_are_reported(self) -> None:
        first = self.shapefile(self.source / "first")
        second = self.shapefile(self.source / "second")

        plan = build_copy_plan([first, second], self.destination)

        self.assertIn("roads.shp", plan.duplicate_names)
        self.assertIn("roads.dbf", plan.duplicate_names)
        self.assertEqual(len(plan.items), 10)

    def test_copying_into_source_folder_is_skipped(self) -> None:
        geo_file = self.shapefile()

        plan = build_copy_plan([geo_file], self.source)

        self.assertEqual(plan.items, ())
        self.assertIn(geo_file.path, plan.skipped_same)
        self.assertEqual(len(plan.skipped_same), 5)
        self.assertEqual(plan.total_size, 0)

    def test_missing_source_is_reported(self) -> None:
        missing = self.source / "missing.shp"
        geo_file = GeoFile(
            path=missing,
            relative_path=missing.relative_to(self.source),
            format=FormatInfo("Shapefile", VECTOR),
            size=0,
        )

        result = copy_plan(
            build_copy_plan([geo_file], self.destination)
        )

        self.assertEqual(len(result.errors), 1)
        self.assertEqual(result.errors[0][0], missing)
        self.assertFalse((self.destination / "missing.shp").exists())


if __name__ == "__main__":
    unittest.main()
