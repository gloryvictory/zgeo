"""Проверки выбора цели перехода из отчёта к замечанию."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from zgeo.issue_navigation import navigation_target
from zgeo.quality_check import QualityIssue


class NavigationTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temp = TemporaryDirectory()
        self.folder = Path(self._temp.name)
        self.main = self.folder / "roads.shp"
        self.main.write_text("", encoding="utf-8")

    def tearDown(self) -> None:
        self._temp.cleanup()

    def test_feature_issue_selects_object(self) -> None:
        issue = QualityIssue(
            "geometry_quality",
            "message",
            layer="roads",
            feature_id=12,
        )

        target = navigation_target(self.main, issue)

        self.assertEqual(target.path, self.main)
        self.assertEqual(target.layer, "roads")
        self.assertEqual(target.feature_id, 12)
        self.assertIsNone(target.sidecar)
        self.assertTrue(target.has_feature)

    def test_extra_feature_ids_are_kept(self) -> None:
        issue = QualityIssue(
            "blank_strings",
            "message",
            layer="roads",
            feature_ids=(3, 4),
        )
        target = navigation_target(self.main, issue)
        self.assertEqual(target.feature_ids(), (3, 4))
        self.assertTrue(target.has_layer)
        self.assertFalse(target.has_feature)
    def test_layer_issue_opens_layer(self) -> None:
        issue = QualityIssue(
            "attribute_fill",
            "message",
            layer="roads",
        )

        target = navigation_target(self.main, issue)

        self.assertTrue(target.has_layer)
        self.assertFalse(target.has_feature)

    def test_existing_prj_is_selected(self) -> None:
        prj = self.folder / "roads.prj"
        prj.write_text("", encoding="utf-8")
        issue = QualityIssue("prj_file", "message", location=".prj")

        target = navigation_target(self.main, issue)

        self.assertEqual(target.sidecar, prj)

    def test_missing_prj_falls_back_to_file(self) -> None:
        issue = QualityIssue("prj_file", "message", location=".prj")

        target = navigation_target(self.main, issue)

        self.assertIsNone(target.sidecar)
        self.assertTrue(target.reveal_only)

    def test_orphan_sidecar_name_is_used_directly(self) -> None:
        orphan = self.folder / "missing.dbf"
        orphan.write_text("", encoding="utf-8")
        issue = QualityIssue(
            "file_paths",
            "message",
            location="missing.dbf",
            detail_only=True,
        )

        target = navigation_target(self.main, issue)

        self.assertEqual(target.sidecar, orphan)

    def test_raster_aux_xml_is_found(self) -> None:
        raster = self.folder / "relief.tif"
        raster.write_text("", encoding="utf-8")
        aux = self.folder / "relief.tif.aux.xml"
        aux.write_text("", encoding="utf-8")
        issue = QualityIssue(
            "metadata_crs",
            "message",
            location=".aux.xml",
        )

        target = navigation_target(raster, issue)

        self.assertEqual(target.sidecar, aux)

    def test_dbf_location_is_found(self) -> None:
        dbf = self.folder / "roads.dbf"
        dbf.write_text("", encoding="utf-8")
        issue = QualityIssue(
            "dataset_integrity",
            "message",
            location="DBF",
        )

        target = navigation_target(self.main, issue)

        self.assertEqual(target.sidecar, dbf)

    def test_file_issue_without_layer_is_revealed(self) -> None:
        issue = QualityIssue("readability", "message", location="Файл")

        target = navigation_target(self.main, issue)

        self.assertTrue(target.reveal_only)
        self.assertFalse(target.has_layer)
        self.assertIsNone(target.sidecar)


if __name__ == "__main__":
    unittest.main()
