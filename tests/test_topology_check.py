"""Проверки модуля топологии.

Модуль topology_check импортирует QGIS, поэтому тесты разбирают исходник
через ast и не требуют запущенного QGIS.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "topology_check.py"


def _module() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _function(name: str) -> ast.FunctionDef:
    node = next(
        (
            item
            for item in _module().body
            if isinstance(item, ast.FunctionDef) and item.name == name
        ),
        None,
    )
    if node is None:
        raise AssertionError("{} not found".format(name))
    return node


class SpatialIndexTests(unittest.TestCase):
    def test_deprecated_insert_feature_is_not_used(self) -> None:
        calls = [
            node
            for node in ast.walk(_module())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "insertFeature"
        ]
        self.assertEqual(calls, [])

    def test_index_uses_add_feature_with_bounds(self) -> None:
        source = ast.unparse(_function("_build_index"))
        self.assertIn("addFeature", source)
        self.assertIn("boundingBox", source)
        self.assertIn("QgsSpatialIndex", source)

    def test_index_entries_are_guarded(self) -> None:
        source = ast.unparse(_function("_build_index"))
        self.assertIn("except Exception", source)
        self.assertIn("continue", source)


if __name__ == "__main__":
    unittest.main()
