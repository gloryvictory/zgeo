"""Проверки модуля перехода из отчёта к проблемному объекту.

Модуль problem_navigation импортирует QGIS, поэтому тесты разбирают
исходник через ast и не требуют запущенного QGIS.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "problem_navigation.py"


def _module() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _functions() -> dict:
    return {
        node.name: node
        for node in _module().body
        if isinstance(node, ast.FunctionDef)
    }


class ProblemNavigationSourceTests(unittest.TestCase):
    def test_expected_entry_points_exist(self) -> None:
        functions = _functions()
        self.assertIn("navigate_to_issue", functions)
        self.assertIn("load_and_show", functions)
        self.assertIn("select_only", functions)
        self.assertIn("_features_extent", functions)
        self.assertIn("_ensure_canvas_layer", functions)
        self.assertIn("_call_if_any", functions)
        self.assertIn("_extent_in_canvas_crs", functions)
        self.assertIn("_ensure_layer", functions)
        self.assertIn("_focus_layer", functions)
        self.assertIn("_open_sidecar", functions)
        self.assertIn("_reveal", functions)
        self.assertIn("_open_prj", functions)

    def test_layer_navigation_selects_and_zooms(self) -> None:
        functions = _functions()
        source = ast.unparse(functions["_focus_layer"])
        self.assertIn("select_only", source)
        select_source = ast.unparse(functions["select_only"])
        self.assertIn("selectByIds", select_source)
        self.assertIn("removeSelection", select_source)
        self.assertIn("selectedFeatureIds", select_source)
        self.assertIn("_zoom_to_layer", source)
        zoom_source = ast.unparse(functions["_zoom_to_layer"])
        self.assertIn("zoomToFeatureIds", zoom_source)
        self.assertIn("setExtent", zoom_source)
        self.assertIn("_extent_in_canvas_crs", zoom_source)
        self.assertIn("showAttributeTable", source)

    def test_layer_is_added_to_the_map_canvas(self) -> None:
        source = ast.unparse(_functions()["_ensure_canvas_layer"])
        self.assertIn("setLayers", source)
        self.assertIn("layers", source)
        focus = ast.unparse(_functions()["_focus_layer"])
        self.assertIn("_ensure_canvas_layer", focus)

    def test_sidecar_path_name_is_not_called(self) -> None:
        for name in ("_open_sidecar", "_reveal"):
            source = ast.unparse(_functions()[name])
            self.assertNotIn("path.name()", source)

    def test_extent_is_transformed_to_canvas_crs(self) -> None:
        source = ast.unparse(_functions()["_extent_in_canvas_crs"])
        self.assertIn("QgsCoordinateTransform", source)
        self.assertIn("destinationCrs", source)
        self.assertIn("transformBoundingBox", source)

    def test_sidecar_navigation_opens_prj(self) -> None:
        source = ast.unparse(_functions()["_open_sidecar"])
        self.assertIn(".prj", source)
        self.assertIn("open_file", source)
        self.assertIn("_reveal", source)

    def test_load_and_show_does_not_open_the_explorer(self) -> None:
        source = ast.unparse(_functions()["load_and_show"])
        self.assertNotIn("_reveal", source)
        self.assertNotIn("reveal_files", source)
        self.assertNotIn("open_folder", source)
        self.assertIn("_open_prj", source)
        self.assertIn("skipped", source)

    def test_open_prj_ignores_other_files(self) -> None:
        source = ast.unparse(_functions()["_open_prj"])
        self.assertIn(".prj", source)
        self.assertIn("open_file", source)
        self.assertNotIn("reveal_files", source)
        self.assertNotIn("open_folder", source)


if __name__ == "__main__":
    unittest.main()
