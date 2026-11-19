"""Проверки набора проверок окна «Проверки».

Модуль check_dialog импортирует PyQt, поэтому тесты разбирают исходник
через ast и не требуют запущенного QGIS.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "check_dialog.py"


def _module() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _check_constants() -> dict:
    constants = {}
    for node in _module().body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if not target.id.startswith("CHECK_"):
            continue
        if isinstance(node.value, ast.Constant):
            constants[target.id] = node.value.value
    return constants


def _definition_keys() -> list:
    keys = []
    for node in ast.walk(_module()):
        if not isinstance(node, ast.keyword) or node.arg != "key":
            continue
        if isinstance(node.value, ast.Name):
            keys.append(node.value.id)
    return keys


class CheckDefinitionsTests(unittest.TestCase):
    def test_geometry_and_coordinates_are_separate_checks(self) -> None:
        constants = _check_constants()
        self.assertIn("CHECK_GEOMETRY", constants)
        self.assertIn("CHECK_COORDINATES", constants)
        self.assertNotEqual(
            constants["CHECK_GEOMETRY"], constants["CHECK_COORDINATES"]
        )

    def test_both_checks_are_registered(self) -> None:
        keys = _definition_keys()
        self.assertIn("CHECK_GEOMETRY", keys)
        self.assertIn("CHECK_COORDINATES", keys)

    def test_prj_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(constants.get("CHECK_PRJ"), "prj_file")
        self.assertIn("CHECK_PRJ", _definition_keys())

    def test_file_paths_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(constants.get("CHECK_FILE_PATHS"), "file_paths")
        self.assertIn("CHECK_FILE_PATHS", _definition_keys())

    def test_readability_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(constants.get("CHECK_READABILITY"), "readability")
        self.assertIn("CHECK_READABILITY", _definition_keys())

    def test_gpkg_integrity_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_GPKG_INTEGRITY"), "gpkg_integrity"
        )
        self.assertIn("CHECK_GPKG_INTEGRITY", _definition_keys())

    def test_duplicate_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_DUPLICATES"), "duplicate_features"
        )
        self.assertIn("CHECK_DUPLICATES", _definition_keys())

    def test_geojson_quality_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_GEOJSON_QUALITY"), "geojson_quality"
        )
        self.assertIn("CHECK_GEOJSON_QUALITY", _definition_keys())

    def test_attribute_fill_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_ATTRIBUTE_FILL"), "attribute_fill"
        )
        self.assertIn("CHECK_ATTRIBUTE_FILL", _definition_keys())

    def test_topology_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_TOPOLOGY"), "topology_quality"
        )
        self.assertIn("CHECK_TOPOLOGY", _definition_keys())

    def test_new_checks_are_disabled_by_default(self) -> None:
        unchecked = set()
        for node in ast.walk(_module()):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name):
                continue
            if node.func.id != "CheckDefinition":
                continue
            key = ""
            checked = True
            for keyword in node.keywords:
                if keyword.arg == "key" and isinstance(
                    keyword.value, ast.Name
                ):
                    key = keyword.value.id
                if keyword.arg == "checked" and isinstance(
                    keyword.value, ast.Constant
                ):
                    checked = bool(keyword.value.value)
            if key and not checked:
                unchecked.add(key)
        self.assertIn("CHECK_PRJ", unchecked)
        self.assertIn("CHECK_READABILITY", unchecked)
        self.assertIn("CHECK_GPKG_INTEGRITY", unchecked)
        self.assertIn("CHECK_DUPLICATES", unchecked)
        self.assertIn("CHECK_FILE_PATHS", unchecked)
        self.assertIn("CHECK_GEOMETRY", unchecked)
        self.assertIn("CHECK_COORDINATES", unchecked)
        self.assertIn("CHECK_GEOJSON_QUALITY", unchecked)
        self.assertIn("CHECK_ATTRIBUTE_FILL", unchecked)
        self.assertIn("CHECK_TOPOLOGY", unchecked)

    def test_keys_are_unique(self) -> None:
        values = list(_check_constants().values())
        self.assertEqual(len(values), len(set(values)))


if __name__ == "__main__":
    unittest.main()
