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


def _frozenset_names(name: str) -> set:
    for node in _module().body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != name:
            continue
        value = node.value
        if not isinstance(value, ast.Call):
            return set()
        if not isinstance(value.func, ast.Name):
            return set()
        if value.func.id != "frozenset" or not value.args:
            return set()
        collection = value.args[0]
        if not isinstance(collection, ast.Set):
            return set()
        return {
            element.id
            for element in collection.elts
            if isinstance(element, ast.Name)
        }
    return set()


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

    def test_field_name_duplicates_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_FIELD_NAME_DUPLICATES"),
            "field_name_duplicates",
        )
        self.assertIn("CHECK_FIELD_NAME_DUPLICATES", _definition_keys())

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

    def test_control_characters_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_CONTROL_CHARS"), "control_chars"
        )
        self.assertIn("CHECK_CONTROL_CHARS", _definition_keys())

    def test_attribute_duplicates_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_ATTRIBUTE_DUPLICATES"),
            "attribute_duplicates",
        )
        self.assertIn("CHECK_ATTRIBUTE_DUPLICATES", _definition_keys())

    def test_blank_strings_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_BLANK_STRINGS"), "blank_strings"
        )
        self.assertIn("CHECK_BLANK_STRINGS", _definition_keys())

    def test_edge_spaces_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(constants.get("CHECK_EDGE_SPACES"), "edge_spaces")
        self.assertIn("CHECK_EDGE_SPACES", _definition_keys())

    def test_inner_spaces_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_INNER_SPACES"), "inner_spaces"
        )
        self.assertIn("CHECK_INNER_SPACES", _definition_keys())

    def test_numeric_text_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_NUMERIC_TEXT"), "numeric_text"
        )
        self.assertIn("CHECK_NUMERIC_TEXT", _definition_keys())

    def test_text_length_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_TEXT_LENGTH"), "text_length"
        )
        self.assertIn("CHECK_TEXT_LENGTH", _definition_keys())

    def test_date_range_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(constants.get("CHECK_DATE_RANGE"), "date_range")
        self.assertIn("CHECK_DATE_RANGE", _definition_keys())

    def test_suspicious_field_names_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_SUSPICIOUS_FIELD_NAMES"),
            "suspicious_field_names",
        )
        self.assertIn(
            "CHECK_SUSPICIOUS_FIELD_NAMES", _definition_keys()
        )

    def test_text_encoding_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_TEXT_ENCODING"), "text_encoding"
        )
        self.assertIn("CHECK_TEXT_ENCODING", _definition_keys())

    def test_content_mismatch_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_CONTENT_MISMATCH"), "content_mismatch"
        )
        self.assertIn("CHECK_CONTENT_MISMATCH", _definition_keys())

    def test_combined_duplicates_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_DUPLICATES_COMBINED"),
            "duplicate_combined",
        )
        self.assertIn("CHECK_DUPLICATES_COMBINED", _definition_keys())

    def test_results_cells_open_a_details_dialog(self) -> None:
        tree = _module()
        class_node = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                and node.name == "CheckResultsTable"
            ),
            None,
        )
        self.assertIsNotNone(class_node)
        methods = {
            node.name
            for node in class_node.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("_show_cell_details", methods)
        source = ast.unparse(class_node)
        self.assertIn("cellDoubleClicked", source)
        self.assertIn("CheckDetailsDialog", source)

    def test_topology_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_TOPOLOGY"), "topology_quality"
        )
        self.assertIn("CHECK_TOPOLOGY", _definition_keys())

    def test_empty_fields_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_EMPTY_FIELDS"), "empty_fields"
        )
        self.assertIn("CHECK_EMPTY_FIELDS", _definition_keys())

    def test_mixed_types_check_is_registered(self) -> None:
        constants = _check_constants()
        self.assertEqual(
            constants.get("CHECK_MIXED_TYPES"), "mixed_types"
        )
        self.assertIn("CHECK_MIXED_TYPES", _definition_keys())

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
        self.assertIn("CHECK_FIELD_NAME_DUPLICATES", unchecked)
        self.assertIn("CHECK_READABILITY", unchecked)
        self.assertIn("CHECK_GPKG_INTEGRITY", unchecked)
        self.assertIn("CHECK_DUPLICATES", unchecked)
        self.assertIn("CHECK_DUPLICATES_COMBINED", unchecked)
        self.assertIn("CHECK_FILE_PATHS", unchecked)
        self.assertIn("CHECK_CONTENT_MISMATCH", unchecked)
        self.assertIn("CHECK_GEOMETRY", unchecked)
        self.assertIn("CHECK_COORDINATES", unchecked)
        self.assertIn("CHECK_GEOJSON_QUALITY", unchecked)
        self.assertIn("CHECK_ATTRIBUTE_FILL", unchecked)
        self.assertIn("CHECK_EMPTY_FIELDS", unchecked)
        self.assertIn("CHECK_CONTROL_CHARS", unchecked)
        self.assertIn("CHECK_ATTRIBUTE_DUPLICATES", unchecked)
        self.assertIn("CHECK_BLANK_STRINGS", unchecked)
        self.assertIn("CHECK_EDGE_SPACES", unchecked)
        self.assertIn("CHECK_INNER_SPACES", unchecked)
        self.assertIn("CHECK_NUMERIC_TEXT", unchecked)
        self.assertIn("CHECK_MIXED_TYPES", unchecked)
        self.assertIn("CHECK_TEXT_LENGTH", unchecked)
        self.assertIn("CHECK_DATE_RANGE", unchecked)
        self.assertIn("CHECK_SUSPICIOUS_FIELD_NAMES", unchecked)
        self.assertIn("CHECK_TEXT_ENCODING", unchecked)
        self.assertIn("CHECK_TOPOLOGY", unchecked)

    def test_all_checks_belong_to_exactly_one_quality_tab(self) -> None:
        spatial = _frozenset_names("SPATIAL_CHECK_KEYS")
        attribute = _frozenset_names("ATTRIBUTE_CHECK_KEYS")
        definitions = set(_definition_keys())

        self.assertTrue(spatial)
        self.assertTrue(attribute)
        self.assertEqual(spatial & attribute, set())
        self.assertEqual(spatial | attribute, definitions)

    def test_attribute_quality_tab_contains_attribute_checks(self) -> None:
        attribute = _frozenset_names("ATTRIBUTE_CHECK_KEYS")
        self.assertEqual(
            attribute,
            {
                "CHECK_FIELD_NAMES",
                "CHECK_FIELD_NAME_DUPLICATES",
                "CHECK_ATTRIBUTE_FILL",
                "CHECK_EMPTY_FIELDS",
                "CHECK_CONTROL_CHARS",
                "CHECK_ATTRIBUTE_DUPLICATES",
                "CHECK_BLANK_STRINGS",
                "CHECK_EDGE_SPACES",
                "CHECK_INNER_SPACES",
                "CHECK_NUMERIC_TEXT",
                "CHECK_MIXED_TYPES",
                "CHECK_TEXT_LENGTH",
                "CHECK_DATE_RANGE",
                "CHECK_SUSPICIOUS_FIELD_NAMES",
                "CHECK_TEXT_ENCODING",
            },
        )

    def test_keys_are_unique(self) -> None:
        values = list(_check_constants().values())
        self.assertEqual(len(values), len(set(values)))

    def test_results_table_has_excel_and_html_export(self) -> None:
        tree = _module()
        class_node = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                and node.name == "CheckResultsTable"
            ),
            None,
        )
        self.assertIsNotNone(class_node)
        methods = {
            node.name
            for node in class_node.body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("begin", methods)
        self.assertIn("set_result", methods)
        self.assertIn("check_keys", methods)
        self.assertIn("_export_excel", methods)
        self.assertIn("_export_html", methods)

        imports = {
            alias.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom)
            and node.module == "table_export"
            for alias in node.names
        }
        self.assertEqual(
            imports,
            {"export_rows_with_dialog", "export_rows_with_html_dialog"},
        )

        init_node = next(
            (
                node
                for node in class_node.body
                if isinstance(node, ast.FunctionDef) and node.name == "__init__"
            ),
            None,
        )
        self.assertIsNotNone(init_node)
        init_source = ast.unparse(init_node)
        self.assertIn("self.export_button", init_source)
        self.assertIn("self.export_menu", init_source)
        self.assertLess(
            init_source.index("self.table"),
            init_source.index("self.export_button"),
        )

    def test_selection_actions_are_above_the_list(self) -> None:
        tree = _module()
        page_node = next(
            (
                node
                for node in tree.body
                if isinstance(node, ast.ClassDef)
                and node.name == "CheckCategoryPage"
            ),
            None,
        )
        self.assertIsNotNone(page_node)
        init_node = next(
            (
                node
                for node in page_node.body
                if isinstance(node, ast.FunctionDef) and node.name == "__init__"
            ),
            None,
        )
        self.assertIsNotNone(init_node)
        source = ast.unparse(init_node)
        actions_index = source.index("actions = QHBoxLayout()")
        self.assertLess(actions_index, source.index("self.selection ="))
        self.assertIn("QSplitter", source)
        self.assertIn(
            "self.results.header_actions.addWidget(self.run_button)",
            source,
        )


if __name__ == "__main__":
    unittest.main()
