import tempfile
import unittest
from pathlib import Path

from zgeo.html_export import write_html, write_html_sheets
from zgeo.i18n import LANGUAGE_EN, LANGUAGE_RU, set_language


class HtmlExportTests(unittest.TestCase):
    def setUp(self) -> None:
        set_language(LANGUAGE_RU)

    def tearDown(self) -> None:
        set_language(LANGUAGE_RU)

    def test_writes_headers_rows_and_escapes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.html"
            write_html(
                path,
                "Файлы",
                ["Файл", "Значение"],
                [
                    ["roads.shp", "Тест <&>"],
                    ["points.shp", True],
                    ["lines.shp", False],
                    ["empty.shp", None],
                    ["count.shp", 2],
                    ["multiline.shp", "a\nb"],
                ],
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn("<!DOCTYPE html>", text)
            self.assertIn('<meta charset="utf-8">', text)
            self.assertIn("<title>ZGeo — экспорт данных</title>", text)
            self.assertIn("<h2>Файлы", text)
            self.assertIn("roads.shp", text)
            self.assertIn("Тест &lt;&amp;&gt;", text)
            self.assertIn("Да", text)
            self.assertIn("Нет", text)
            self.assertIn('<td class="numeric">2</td>', text)
            self.assertIn("a\nb", text)
            self.assertIn("Строк: 6", text)
            self.assertIn("Сформировано:", text)

    def test_writes_multiple_sheets_with_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.html"
            write_html_sheets(
                path,
                [
                    ("Файлы", ["Файл"], [["roads.shp"]]),
                    (
                        "Статистика",
                        ["Формат", "Кол-во"],
                        [["ESRI Shapefile", 2]],
                    ),
                ],
                title="Отчёт <ZGeo>",
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn("<title>Отчёт &lt;ZGeo&gt;</title>", text)
            self.assertIn('<a href="#sheet-1">Файлы</a>', text)
            self.assertIn('<a href="#sheet-2">Статистика</a>', text)
            self.assertIn('<section id="sheet-2">', text)
            self.assertIn("<h2>Статистика", text)
            self.assertIn("ESRI Shapefile", text)
            self.assertIn("Строк: 1", text)

    def test_duplicate_names_and_empty_sheet(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.html"
            write_html_sheets(
                path,
                [
                    ("Файлы", ["A"], [["1"]]),
                    ("Файлы", ["B"], [["2"]]),
                    ("", [], []),
                ],
            )

            text = path.read_text(encoding="utf-8")
            self.assertIn('<a href="#sheet-2">Файлы (2)</a>', text)
            self.assertIn('<section id="sheet-3">', text)
            self.assertIn('<p class="empty">Нет данных</p>', text)

    def test_english_document_and_boolean_cells(self) -> None:
        set_language(LANGUAGE_EN)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.html"
            write_html(path, "", ["Value"], [[True], [False]])

            text = path.read_text(encoding="utf-8")
            self.assertIn('<html lang="en">', text)
            self.assertIn(
                "<title>ZGeo — data export</title>", text
            )
            self.assertIn("<h2>Data", text)
            self.assertIn("Yes", text)
            self.assertIn("No", text)
            self.assertIn("Generated:", text)
            self.assertIn("Rows: 2", text)


if __name__ == "__main__":
    unittest.main()
