import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from zgeo.excel_export import write_xlsx

MAIN_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


class ExcelExportTests(unittest.TestCase):
    def test_writes_workbook_with_headers_and_rows(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.xlsx"
            write_xlsx(
                path,
                "Форматы",
                ["Формат", "Кол-во", "Объем ориентировочно"],
                [
                    ["GeoTIFF / TIFF", 2, "1.5 КБ"],
                    ["GeoPackage", 1, "96 КБ"],
                    ["Тест <&>", None, "100 Б"],
                ],
            )

            with zipfile.ZipFile(path) as archive:
                names = set(archive.namelist())
                self.assertIn("[Content_Types].xml", names)
                self.assertIn("xl/workbook.xml", names)
                self.assertIn("xl/worksheets/sheet1.xml", names)

                sheet = ElementTree.fromstring(
                    archive.read("xl/worksheets/sheet1.xml")
                )
                rows = sheet.findall(".//{}row".format(MAIN_NS))
                self.assertEqual(len(rows), 4)

                headers = [
                    cell.findtext(
                        ".//{}t".format(MAIN_NS)
                    )
                    for cell in rows[0].findall("{}c".format(MAIN_NS))
                ]
                self.assertEqual(
                    headers,
                    ["Формат", "Кол-во", "Объем ориентировочно"],
                )

                second_row = rows[1].findall("{}c".format(MAIN_NS))
                self.assertEqual(
                    second_row[0].findtext(
                        ".//{}t".format(MAIN_NS)
                    ),
                    "GeoTIFF / TIFF",
                )
                self.assertEqual(
                    second_row[1].findtext(
                        "{}v".format(MAIN_NS)
                    ),
                    "2",
                )

                third_row = rows[3].findall("{}c".format(MAIN_NS))
                self.assertEqual(
                    third_row[0].findtext(
                        ".//{}t".format(MAIN_NS)
                    ),
                    "Тест <&>",
                )
                self.assertEqual(len(third_row), 2)

    def test_sanitizes_sheet_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "table.xlsx"
            write_xlsx(path, "Данные/2026:тест", ["A"], [["B"]])

            with zipfile.ZipFile(path) as archive:
                workbook = archive.read("xl/workbook.xml").decode("utf-8")
                self.assertIn('name="Данные_2026_тест"', workbook)
