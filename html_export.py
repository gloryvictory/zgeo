"""Экспорт таблиц в автономный HTML без внешних зависимостей."""

from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

from .excel_export import CellValue, SheetSpec
from .i18n import get_language, tr

_CSS = """
:root {
    color-scheme: light;
}
* {
    box-sizing: border-box;
}
html {
    scroll-behavior: smooth;
}
body {
    margin: 0;
    background: #f4f7fa;
    color: #1f2933;
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 14px;
    line-height: 1.45;
}
header {
    padding: 26px 32px 22px;
    background: #0f4c81;
    color: #ffffff;
}
header h1 {
    margin: 0 0 6px;
    font-size: 24px;
    line-height: 1.2;
}
.meta {
    color: #d9eaf7;
    font-size: 13px;
}
nav {
    position: sticky;
    top: 0;
    z-index: 10;
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 10px 24px;
    background: #ffffff;
    border-bottom: 1px solid #d9e2ec;
}
nav a {
    padding: 4px 9px;
    color: #0f4c81;
    text-decoration: none;
    border-radius: 6px;
    white-space: nowrap;
}
nav a:hover {
    background: #e6f0f8;
}
main {
    display: flex;
    flex-direction: column;
    gap: 22px;
    padding: 22px 24px 32px;
}
section {
    overflow: hidden;
    background: #ffffff;
    border: 1px solid #d9e2ec;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(15, 76, 129, 0.08);
}
section h2 {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 16px;
    margin: 0;
    padding: 13px 18px;
    background: #eef5fb;
    border-bottom: 1px solid #d9e2ec;
    font-size: 18px;
}
.count {
    color: #52667a;
    font-size: 12px;
    font-weight: normal;
    white-space: nowrap;
}
.table-wrap {
    max-height: 72vh;
    overflow: auto;
}
table {
    width: 100%;
    min-width: 640px;
    border-collapse: collapse;
    font-size: 13px;
}
th,
td {
    padding: 7px 9px;
    border: 1px solid #cbd5e1;
    text-align: left;
    vertical-align: top;
    overflow-wrap: anywhere;
    white-space: pre-wrap;
}
th {
    position: sticky;
    top: 0;
    z-index: 1;
    background: #d9eaf7;
    font-weight: 600;
}
td.numeric {
    text-align: right;
    white-space: nowrap;
}
tbody tr:nth-child(even) {
    background: #f8fafc;
}
tbody tr:hover {
    background: #eef6ff;
}
td.empty,
p.empty {
    padding: 22px 18px;
    color: #64748b;
    text-align: center;
}
footer {
    padding: 0 24px 24px;
    color: #7b8a99;
    font-size: 12px;
    text-align: right;
}
@media print {
    body {
        background: #ffffff;
    }
    nav {
        display: none;
    }
    main {
        padding: 0;
    }
    section {
        box-shadow: none;
        break-inside: avoid;
    }
    .table-wrap {
        max-height: none;
        overflow: visible;
    }
    th {
        position: static;
    }
}
"""


def write_html(
    path: Path,
    sheet_name: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[CellValue]],
    *,
    title: Optional[str] = None,
) -> None:
    """Записать одну таблицу в файл .html."""

    write_html_sheets(
        path, [(sheet_name, headers, rows)], title=title
    )


def write_html_sheets(
    path: Path,
    sheets: Iterable[SheetSpec],
    *,
    title: Optional[str] = None,
) -> None:
    """Записать несколько таблиц в один автономный HTML-файл."""

    normalized = _normalize_sheets(sheets)
    document_title = title or tr("ZGeo — экспорт данных")
    generated = datetime.now().strftime("%d.%m.%Y %H:%M")

    navigation: List[str] = []
    sections: List[str] = []
    for index, (name, headers, rows) in enumerate(normalized, start=1):
        anchor = "sheet-{}".format(index)
        navigation.append(
            '<a href="#{anchor}">{name}</a>'.format(
                anchor=anchor, name=escape(name)
            )
        )
        sections.append(
            _section_html(anchor, name, headers, rows)
        )

    document = _document_html(
        document_title,
        generated,
        navigation,
        sections,
    )
    Path(path).write_text(document, encoding="utf-8")


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
            safe_name = base_name + suffix
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


def _safe_sheet_name(name: str) -> str:
    cleaned = " ".join(str(name).split())
    return cleaned or tr("Данные")


def _section_html(
    anchor: str,
    name: str,
    headers: Sequence[str],
    rows: Sequence[Sequence[CellValue]],
) -> str:
    column_count = max(
        [len(headers)] + [len(row) for row in rows] + [0]
    )
    if column_count == 0:
        return (
            '<section id="{anchor}">'
            "<h2>{name}</h2>"
            '<p class="empty">{empty}</p>'
            "</section>"
        ).format(
            anchor=anchor,
            name=escape(name),
            empty=escape(tr("Нет данных")),
        )

    header_html = ""
    if headers:
        padded_headers = list(headers) + [""] * (
            column_count - len(headers)
        )
        header_html = "<thead><tr>{}</tr></thead>".format(
            "".join(_header_cell_html(value) for value in padded_headers)
        )

    body_rows: List[str] = []
    for row in rows:
        padded_row = list(row) + [""] * (column_count - len(row))
        body_rows.append(
            "<tr>{}</tr>".format(
                "".join(_cell_html(value) for value in padded_row)
            )
        )
    if not body_rows:
        body_rows.append(
            '<tr><td class="empty" colspan="{}">{}</td></tr>'.format(
                column_count, escape(tr("Нет данных"))
            )
        )

    return (
        '<section id="{anchor}">'
        "<h2>{name}<span class=\"count\">{count}</span></h2>"
        '<div class="table-wrap">'
        "<table>"
        "{header}"
        "<tbody>{body}</tbody>"
        "</table>"
        "</div>"
        "</section>"
    ).format(
        anchor=anchor,
        name=escape(name),
        count=escape(tr("Строк: {}", len(rows))),
        header=header_html,
        body="".join(body_rows),
    )


def _document_html(
    title: str,
    generated: str,
    navigation: Sequence[str],
    sections: Sequence[str],
) -> str:
    language = "en" if get_language() == "en" else "ru"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="' + language + '">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>" + escape(title) + "</title>\n"
        "<style>" + _CSS + "</style>\n"
        "</head>\n"
        "<body>\n"
        "<header>\n"
        "<h1>" + escape(title) + "</h1>\n"
        '<div class="meta">'
        + escape(tr("Сформировано: {}", generated))
        + "</div>\n"
        "</header>\n"
        "<nav>" + "".join(navigation) + "</nav>\n"
        "<main>" + "".join(sections) + "</main>\n"
        "<footer>ZGeo</footer>\n"
        "</body>\n"
        "</html>\n"
    )


def _cell_text(value: CellValue) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return tr("Да") if value else tr("Нет")
    return str(value)


def _header_cell_html(value: CellValue) -> str:
    return "<th>{}</th>".format(escape(_cell_text(value)))


def _cell_html(value: CellValue) -> str:
    text = _cell_text(value)
    css_class = ' class="numeric"' if _is_number(value) else ""
    return "<td{}>{}</td>".format(css_class, escape(text))


def _is_number(value: CellValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
