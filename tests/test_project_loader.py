"""Проверки модуля загрузки файлов в проект.

Модуль project_loader импортирует QGIS, поэтому тесты разбирают исходник
через ast и не требуют запущенного QGIS.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "project_loader.py"


def _module() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _functions() -> dict:
    return {
        node.name: node
        for node in _module().body
        if isinstance(node, ast.FunctionDef)
    }


class ProjectLoaderSourceTests(unittest.TestCase):
    def test_expected_entry_points_exist(self) -> None:
        functions = _functions()
        self.assertIn("load_files_into_project", functions)
        self.assertIn("_file_layers", functions)
        self.assertIn("_normalized_source", functions)

    def test_loader_adds_vector_and_raster_layers(self) -> None:
        source = ast.unparse(_functions()["_file_layers"])
        self.assertIn("QgsRasterLayer", source)
        self.assertIn("vector_layers", source)
        self.assertIn("RASTER", source)

    def test_loader_skips_existing_sources_and_keeps_errors(self) -> None:
        source = ast.unparse(_functions()["load_files_into_project"])
        self.assertIn("addMapLayer", source)
        self.assertIn("existing", source)
        self.assertIn("skipped", source)
        self.assertIn("errors", source)

    def test_load_result_reports_counts(self) -> None:
        class_node = next(
            (
                node
                for node in _module().body
                if isinstance(node, ast.ClassDef)
                and node.name == "LoadResult"
            ),
            None,
        )
        self.assertIsNotNone(class_node)
        names = {
            node.target.id
            for node in class_node.body
            if isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
        }
        self.assertEqual(names, {"added", "skipped", "errors"})


if __name__ == "__main__":
    unittest.main()

