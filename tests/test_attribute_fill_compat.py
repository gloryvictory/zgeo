"""Проверки совместимости атрибутивных проверок с Qt5 и Qt6.

``attribute_fill.py`` импортирует QGIS, поэтому тесты разбирают исходник
через ``ast``. В QGIS 4 / PyQt6 у класса ``QVariant`` нет атрибута
``String``, поэтому сравнение типа поля должно идти через ``QMetaType.Type``
с запасным вариантом ``QVariant`` для Qt5.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "attribute_fill.py"


def _module() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _functions() -> dict:
    return {
        node.name: node
        for node in _module().body
        if isinstance(node, ast.FunctionDef)
    }


class AttributeFillCompatibilityTests(unittest.TestCase):
    def test_field_types_do_not_use_qvariant_string_directly(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "QVariant.String",
            "QVariant.Date",
            "QVariant.DateTime",
        ):
            self.assertNotIn(forbidden, source)

    def test_field_types_use_qmetatype_with_fallback(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertIn("QMetaType", source)
        self.assertIn("_STRING_TYPES", source)
        self.assertIn("_DATE_TYPES", source)

    def test_field_type_helper_has_both_qt_branches(self) -> None:
        helper = _functions().get("_field_type_set")
        self.assertIsNotNone(helper)
        source = ast.unparse(helper)
        self.assertIn("QMetaType.Type", source)
        self.assertIn("QVariant", source)


class ReadFailureTests(unittest.TestCase):
    def test_layer_read_errors_become_issues(self) -> None:
        functions = _functions()
        self.assertIn("_ReadFailure", {
            node.name
            for node in _module().body
            if isinstance(node, ast.ClassDef)
        })

        append = ast.unparse(functions["_append_read_failures"])
        self.assertIn("read_failure_issue", append)

        collect = ast.unparse(functions["_collect"])
        self.assertIn("_safe_inspect_layer", collect)
        self.assertIn("read_errors", collect)

    def test_every_reading_check_reports_read_errors(self) -> None:
        functions = _functions()
        for name in (
            "inspect_attribute_fill",
            "inspect_empty_fields",
            "inspect_control_characters",
            "inspect_blank_strings",
            "inspect_edge_spaces",
            "inspect_inner_spaces",
            "inspect_numeric_text",
            "inspect_mixed_types",
            "inspect_text_encoding",
            "inspect_text_length",
            "inspect_date_range",
            "inspect_suspicious_field_names",
        ):
            with self.subTest(check=name):
                source = ast.unparse(functions[name])
                self.assertIn("_append_read_failures", source)
                self.assertIn("read_errors", source)

    def test_layer_inspectors_raise_read_failure(self) -> None:
        source = SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("except Exception:\n        return None", source)
        self.assertGreaterEqual(source.count("_ReadFailure("), 8)


if __name__ == "__main__":
    unittest.main()

