"""Экспорт простых таблиц в Excel без внешних зависимостей."""

from __future__ import annotations

import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Union
from xml.sax.saxutils import escape

from .i18n import tr

CellValue = Union[str, int, float, None]
SheetSpec = Tuple[str, Sequence[str], Iterable[Sequence[CellValue]]]

_INVALID_SHEET_CHARS = set('[]:*?/\\')


def write_xlsx(
    path: Path,
    sheet_name: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
) -> None:
    """Записать одну таблицу в файл .xlsx."""

    write_xlsx_sheets(path, [(sheet_name, headers, rows)])


def write_xlsx_sheets(
    path: Path,
    sheets: Iterable[SheetSpec],
) -> None:
    """Записать несколько таблиц в отдельные листы файла .xlsx.

    Формат собирается стандартными средствами Python: используется
    минимальный набор XML-частей и inline-строк, поэтому openpyxl или
    другие библиотеки не требуются.
    """

    path = Path(path)
    normalized = _normalize_sheets(sheets)
    parts = {
        "[Content_Types].xml": _content_types_xml(len(normalized)),
        "_rels/.rels": _root_rels_xml(),
        "docProps/core.xml": _core_properties_xml(),
        "docProps/app.xml": _app_properties_xml(),
        "xl/workbook.xml": _workbook_xml(
            [name for name, _headers, _rows in normalized]
        ),
        "xl/_rels/workbook.xml.rels": _workbook_rels_xml(len(normalized)),
        "xl/styles.xml": _styles_xml(),
    }
    for index, (name, headers, rows) in enumerate(normalized, start=1):
        column_widths = _column_widths(headers, rows)
        parts["xl/worksheets/sheet{}.xml".format(index)] = _worksheet_xml(
            headers, rows, column_widths
        )

    with zipfile.ZipFile(
        path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for name, content in parts.items():
            archive.writestr(name, content.encode("utf-8"))


def _normalize_sheets(
    sheets: Iterable[SheetSpec],
) -> List[Tuple[str, List[str], List[List[CellValue]]]]:
    normalized: List[Tuple[str, List[str], List[List[CellValue]]]] = []
    used_names = set()
    for sheet_name, headers, rows in sheets:
        safe_name = _safe_sheet_name(sheet_name)
        base_name = safe_name
        counter = 2
        while safe_name.casefold() in used_names:
            suffix = " ({})".format(counter)
            safe_name = base_name[: 31 - len(suffix)] + suffix
            counter += 1
        used_names.add(safe_name.casefold())
        normalized.append(
            (
                safe_name,
                [str(header) for header in headers],
                [list(row) for row in rows],
            )
        )
    if not normalized:
        normalized.append((tr("Данные"), [], []))
    return normalized


def _worksheet_xml(
    headers: Sequence[str],
    rows: Sequence[Sequence[CellValue]],
    column_widths: Sequence[int],
) -> str:
    last_column = _column_letter(max(1, len(headers)))
    last_row = max(1, len(rows) + 1)

    columns = "".join(
        '<col min="{min}" max="{min}" width="{width}" customWidth="1"/>'.format(
            min=index + 1, width=width
        )
        for index, width in enumerate(column_widths)
    )

    header_cells = "".join(
        _cell_xml(1, index + 1, header, style=1)
        for index, header in enumerate(headers)
    )
    data_rows = []
    for row_index, row in enumerate(rows, start=2):
        cells = "".join(
            _cell_xml(row_index, column_index + 1, value)
            for column_index, value in enumerate(row)
        )
        data_rows.append('<row r="{0}">{1}</row>'.format(row_index, cells))

    auto_filter = ""
    if headers:
        auto_filter = '<autoFilter ref="A1:{}{}"/>'.format(
            last_column, last_row
        )

    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetViews>"
        '<sheetView workbookViewId="0">'
        '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>'
        '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
        "</sheetView>"
        "</sheetViews>"
        "<cols>{columns}</cols>"
        "<sheetData>"
        '<row r="1" ht="20" customHeight="1">{header_cells}</row>'
        "{data_rows}"
        "</sheetData>"
        "{auto_filter}"
        "</worksheet>"
    ).format(
        columns=columns,
        header_cells=header_cells,
        data_rows="".join(data_rows),
        auto_filter=auto_filter,
    )


def _cell_xml(
    row_index: int, column_index: int, value: CellValue, style: int = 0
) -> str:
    reference = "{}{}".format(_column_letter(column_index), row_index)
    style_attr = ' s="{}"'.format(style) if style else ""

    if value is None:
        return ""

    if isinstance(value, bool):
        value = tr("Да") if value else tr("Нет")

    if isinstance(value, (int, float)):
        return '<c r="{}"{}><v>{}</v></c>'.format(
            reference, style_attr, value
        )

    text = escape(str(value))
    return (
        '<c r="{ref}"{style} t="inlineStr">'
        '<is><t xml:space="preserve">{text}</t></is>'
        "</c>"
    ).format(ref=reference, style=style_attr, text=text)


def _column_widths(
    headers: Sequence[str], rows: Sequence[Sequence[CellValue]]
) -> List[int]:
    column_count = max(1, len(headers))
    widths: List[int] = []
    for column_index in range(column_count):
        values = [headers[column_index] if column_index < len(headers) else ""]
        for row in rows:
            value = row[column_index] if column_index < len(row) else ""
            values.append("" if value is None else str(value))
        longest = max(
            (max((len(line) for line in value.splitlines()), default=0)
             for value in values),
            default=0,
        )
        widths.append(max(10, min(60, longest + 2)))
    return widths


def _column_letter(index: int) -> str:
    letters = ""
    while index > 0:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters or "A"


def _safe_sheet_name(name: str) -> str:
    cleaned = "".join(
        "_" if char in _INVALID_SHEET_CHARS else char for char in name
    ).strip()
    return (cleaned or tr("Данные"))[:31]


def _content_types_xml(sheet_count: int = 1) -> str:
    worksheet_overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet{}.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'.format(
            index
        )
        for index in range(1, max(1, sheet_count) + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        "{}"
        '<Override PartName="/xl/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
        '<Override PartName="/docProps/core.xml" '
        'ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
        '<Override PartName="/docProps/app.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>'
        "</Types>"
    ).format(worksheet_overrides)


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        '<Relationship Id="rId2" '
        'Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" '
        'Target="docProps/core.xml"/>'
        '<Relationship Id="rId3" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" '
        'Target="docProps/app.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: Sequence[str]) -> str:
    sheets = "".join(
        '<sheet name="{name}" sheetId="{sheet_id}" r:id="rId{sheet_id}"/>'.format(
            name=escape(name, {'"': "&quot;"}),
            sheet_id=index,
        )
        for index, name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<sheets>{}</sheets>"
        "</workbook>"
    ).format(sheets)


def _workbook_rels_xml(sheet_count: int = 1) -> str:
    sheet_rels = "".join(
        '<Relationship Id="rId{index}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet{index}.xml"/>'.format(index=index)
        for index in range(1, max(1, sheet_count) + 1)
    )
    styles_id = max(1, sheet_count) + 1
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        "{sheet_rels}"
        '<Relationship Id="rId{styles_id}" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
        'Target="styles.xml"/>'
        "</Relationships>"
    ).format(sheet_rels=sheet_rels, styles_id=styles_id)


def _styles_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        '<fonts count="2">'
        '<font><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        '<font><b/><sz val="11"/><name val="Calibri"/><family val="2"/></font>'
        "</fonts>"
        '<fills count="3">'
        '<fill><patternFill patternType="none"/></fill>'
        '<fill><patternFill patternType="gray125"/></fill>'
        '<fill><patternFill patternType="solid">'
        '<fgColor rgb="FFD9EAF7"/><bgColor indexed="64"/>'
        "</patternFill></fill>"
        "</fills>"
        '<borders count="2">'
        "<border><left/><right/><top/><bottom/><diagonal/></border>"
        "<border>"
        '<left style="thin"><color rgb="FFB7C9D6"/></left>'
        '<right style="thin"><color rgb="FFB7C9D6"/></right>'
        '<top style="thin"><color rgb="FFB7C9D6"/></top>'
        '<bottom style="thin"><color rgb="FFB7C9D6"/></bottom>'
        "<diagonal/>"
        "</border>"
        "</borders>"
        '<cellStyleXfs count="1">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
        "</cellStyleXfs>"
        '<cellXfs count="2">'
        '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>'
        '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" '
        'applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1">'
        '<alignment vertical="center"/>'
        "</xf>"
        "</cellXfs>"
        '<cellStyles count="1">'
        '<cellStyle name="Normal" xfId="0" builtinId="0"/>'
        "</cellStyles>"
        "</styleSheet>"
    )


def _core_properties_xml() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties '
        'xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/" '
        'xmlns:dcterms="http://purl.org/dc/terms/" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
        "<dc:creator>ZGeo</dc:creator>"
        "<cp:lastModifiedBy>ZGeo</cp:lastModifiedBy>"
        '<dcterms:created xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:created>'
        '<dcterms:modified xsi:type="dcterms:W3CDTF">{timestamp}</dcterms:modified>'
        "</cp:coreProperties>"
    ).format(timestamp=timestamp)


def _app_properties_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
        'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
        "<Application>ZGeo</Application>"
        "</Properties>"
    )
