"""Проверки регистрации ZGeo в интерфейсе QGIS.

Модуль plugin импортирует QGIS, поэтому тесты разбирают исходник через
ast и не требуют запущенного QGIS.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest

SOURCE_PATH = Path(__file__).resolve().parents[1] / "plugin.py"


def _module() -> ast.Module:
    return ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))


def _class_node() -> ast.ClassDef:
    node = next(
        (
            item
            for item in _module().body
            if isinstance(item, ast.ClassDef) and item.name == "ZGeoPlugin"
        ),
        None,
    )
    if node is None:
        raise AssertionError("ZGeoPlugin class not found")
    return node


def _methods() -> dict:
    return {
        node.name: node
        for node in _class_node().body
        if isinstance(node, ast.FunctionDef)
    }


def _constant(name: str):
    for node in _module().body:
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(node.value)
    return None


class PluginRegistrationTests(unittest.TestCase):
    def test_toolbar_visibility_is_restored_after_startup(self) -> None:
        methods = _methods()
        self.assertIn("_schedule_startup_checks", methods)
        self.assertIn("_connect_startup_signals", methods)
        self.assertIn("_disconnect_startup_signals", methods)

        delays = _constant("STARTUP_CHECKS_MS")
        self.assertIsInstance(delays, tuple)
        self.assertGreaterEqual(len(delays), 4)
        self.assertEqual(delays[0], 0)
        self.assertGreaterEqual(max(delays), 5000)

    def test_startup_checks_run_from_init_gui(self) -> None:
        source = ast.unparse(_methods()["initGui"])
        self.assertIn("_schedule_startup_checks", source)
        self.assertIn("_connect_startup_signals", source)
        self.assertIn("_build_toolbar", source)
        self.assertIn("_restore_toolbar_visibility", source)
        self.assertIn("_connect_quit_signal", source)

    def test_startup_signals_are_connected_and_released(self) -> None:
        connect_source = ast.unparse(
            _methods()["_connect_startup_signals"]
        )
        self.assertIn("initializationCompleted", connect_source)
        self.assertIn("projectRead", connect_source)
        self.assertIn("_ensure_toolbar_visible", connect_source)

        unload_source = ast.unparse(_methods()["unload"])
        self.assertIn("_disconnect_startup_signals", unload_source)

    def test_restored_toolbar_is_reused_instead_of_deleted(self) -> None:
        module_functions = {
            node.name: node
            for node in _module().body
            if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("_find_live_toolbar", module_functions)
        finder = ast.unparse(module_functions["_find_live_toolbar"])
        self.assertIn("findChildren", finder)
        self.assertIn("TOOLBAR_OBJECT_NAME", finder)
        self.assertIn("parentWidget", finder)

        build = ast.unparse(_methods()["_build_toolbar"])
        self.assertIn("_find_live_toolbar", build)
        self.assertNotIn("removeToolBar", build)
        self.assertNotIn("deleteLater", build)

    def test_visibility_preference_is_persisted(self) -> None:
        key = _constant("TOOLBAR_VISIBLE_KEY")
        self.assertEqual(key, "zgeo/toolbar_visible")

        methods = _methods()
        for name in (
            "_toolbar_preference",
            "_restore_toolbar_visibility",
            "_on_toolbar_visibility_changed",
        ):
            self.assertIn(name, methods)

        changed = ast.unparse(methods["_on_toolbar_visibility_changed"])
        self.assertIn("setValue", changed)
        self.assertIn("_shutting_down", changed)
        self.assertIn("_startup_grace_until", changed)

        init_source = ast.unparse(methods["initGui"])
        self.assertIn("_restore_toolbar_visibility", init_source)

    def test_shutdown_does_not_hide_the_toolbar(self) -> None:
        methods = _methods()
        self.assertIn("_connect_quit_signal", methods)
        self.assertIn("_on_about_to_quit", methods)

        quit_source = ast.unparse(methods["_on_about_to_quit"])
        self.assertIn("_shutting_down", quit_source)

        unload_source = ast.unparse(methods["unload"])
        self.assertIn("_disconnect_quit_signal", unload_source)
        self.assertIn("DETACHED_OBJECT_NAME", unload_source)
    def test_toolbar_is_shown_again_when_hidden(self) -> None:
        source = ast.unparse(_methods()["_ensure_toolbar_visible"])
        self.assertIn("isHidden", source)
        self.assertIn("show", source)
        self.assertIn("_add_toolbar", source)
        self.assertIn("setVisible", source)

    def test_toolbar_object_name_is_stable(self) -> None:
        name = _constant("TOOLBAR_OBJECT_NAME")
        self.assertEqual(name, "ZGeoToolbar")
        source = ast.unparse(_class_node())
        self.assertIn("TOOLBAR_OBJECT_NAME", source)


if __name__ == "__main__":
    unittest.main()
