# ZGeo

**Language:** [Русский](README.md) | **English**

A QGIS plugin for quickly browsing the contents of a spatial data folder.

Plugin version: **1.15.0**

The plugin adds a dedicated **“ZGeo”** toolbar to QGIS with a **“ZGeo-Каталог”** (ZGeo Catalog) button that opens a floating panel. The panel provides:

- the plugin version is shown at the top;
- the **“Выбрать папку”** button opens the system folder picker;
- the selected folder name and full path are shown at the top of the panel;
- all supported spatial files are found recursively, including subfolders;
- while scanning, the current file name and the number of supported spatial files found are shown, and the **“Прервать”** button stops the scan;
- results are displayed as a list: relative path, format, coordinate reference system, feature count and file size;
- after scanning, the CRS, feature count and full dataset size are read automatically; progress is shown in the status bar;
- the number of files and their total size are shown above the list; when filtering, the total size is calculated for visible files only;
- the full dataset size includes sidecar files (SHP + DBF + SHX + PRJ + CPG and others, MIF + MID, TAB + DAT/MAP/ID/IND);
- the status bar is at the bottom of the window: the current operation is shown on the left, and **“Выбрано: N из M”** is shown on the right;
- the list can be filtered by name, format, path or attribute issues;
- the **“Настройки”** tab lets you select the formats to scan; the **“Выбрать все”**, **“Сбросить все”**, **“Только вектор”** and **“Только растр”** buttons are available at the top; **Excel** is disabled by default;
- the **“Файлы”** tab has the **“Информация”**, **“Открыть в проводнике”**, **“Экспорт в Excel”** and **“Проверить атрибуты”** buttons at the bottom;
- **“Проверить атрибуты”** checks the field names of vector files and adds a **“Проблемы с атрибутами”** column with the values **“Да”**, **“Нет”** or **“—”**;
- after the attribute check, the **“Проблемных файлов: N”** line is shown and the **“Только проблемные”** filter becomes available;
- reading characteristics and the attribute check can be interrupted with the cancel button;
- for a selected file, the panel shows the CRS, feature count, geometry, extent and an attribute field table with names, aliases, types, lengths, precision and comments;
- **“Открыть в проводнике”** opens Windows Explorer with the file selected; files from different folders open in separate Explorer windows;
- the **“Статистика”** tab shows charts by file size and type, followed by a statistics table by format; after reading characteristics, full dataset sizes are used;
- the file list, statistics table and attribute field table can be exported to Excel; when exporting the list, format statistics are added as a separate worksheet, totals are added to the list and statistics, and Explorer opens with the selected file after saving; if the **“Проблемы с атрибутами”** column has been added, it is included in the export as well;
- the refresh button rescans the current folder.

QGIS 3.16 and newer are supported, including QGIS 4 / Qt 6.

> The plugin interface is currently in Russian. UI labels in this document are quoted exactly as they appear in the interface.

## Screenshots

### Files tab

Attribute check results, the problematic file counter and the **“Только проблемные”** filter.

<img src="img/screen_1.png" alt="Files tab with the Only problematic filter" width="720">

### Statistics tab

Charts by file size and type, plus the statistics table by format.

<img src="img/screen_2.png" alt="Statistics tab" width="720">

### Settings tab

Format selection for scanning and quick-selection buttons.

<img src="img/screen_3.png" alt="Settings tab" width="720">

## Installing in QGIS

### From a ZIP archive

Build the archive:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build_zip.ps1
```

The ready file will be created at `dist\zgeo-1.15.0.zip`. In QGIS, open:

**Plugins → Manage and Install Plugins → Install from ZIP**

and select the built archive.

### Manually

Copy the entire `zgeo` folder to the QGIS plugins directory:

- Windows QGIS 4: `%APPDATA%\QGIS\QGIS4\profiles\default\python\plugins\`
- Windows QGIS 3: `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
- Linux: `~/.local/share/QGIS/QGIS4/profiles/default/python/plugins/`
- macOS: `~/Library/Application Support/QGIS/QGIS4/profiles/default/python/plugins/`

Then enable **ZGeo** in the QGIS plugin manager.

After updating the plugin, close QGIS completely and start it again. If the **“ZGeo”** toolbar does not appear, open **Plugins → Manage and Install Plugins**, find **ZGeo** and make sure it is enabled.

## Usage

1. Click **“ZGeo-Каталог”** on the **“ZGeo”** toolbar (or choose **Plugins → ZGeo → ZGeo-Каталог**).
2. In the floating panel, click **“Выбрать папку”**.
3. Select a folder with geodata.
4. During scanning, the current file name and the number of supported files found are shown. The scan can be stopped with **“Прервать”**.
5. When scanning finishes, the folder name appears at the top and the found files are shown in the list. The CRS, feature count and full dataset size are read automatically; progress is visible in the status bar, and the cancel button can interrupt reading. If needed, enter part of a file name or format in the filter field.
6. Open the **“Настройки”** tab to choose the formats to scan. **Excel** is disabled by default; after changing the settings, rescan the folder with the refresh button.
7. Click **“Проверить атрибуты”** to check vector field names and add the **“Проблемы с атрибутами”** column. After the check, the **“Проблемных файлов: N”** line appears and the **“Только проблемные”** filter becomes available.
8. Select a file and click **“Информация”** at the bottom of the list.
9. Click **“Открыть в проводнике”** to show the file in Windows Explorer.
10. Click **“Экспорт в Excel”** to export the found files with a total row and a separate statistics worksheet. After saving, Explorer opens with the selected `.xlsx`.
11. Open the **“Статистика”** tab to view the charts.

The last selected folder is remembered and used as the starting folder next time.

## Status bar

The status bar is at the bottom of the window. The current operation is shown on the left: scanning, reading characteristics and sizes, attribute check, retrieving information, opening Explorer, Excel export, cancellation messages and errors. The number of selected rows is always shown on the right: **“Выбрано: N из M”**. The counter is updated when files are selected and when the list is filtered.

## Scanning

Scanning runs in a background thread, so the QGIS interface remains responsive. While scanning, the panel shows the current file name and the number of files matching the supported spatial formats. Unsupported files do not increment the **“Найдено”** counter. **“Прервать”** stops the scan; already found files remain in the list, and statistics are built from the partial result.

After the list appears, the panel reads the CRS and feature count one file at a time through QGIS providers. The values appear in the **“Система координат”** and **“Элементов”** columns; the current file and overall progress are shown in the status bar. A cancel button appears next to the buttons at the bottom and interrupts long reads; values already read are kept. For raster files, the feature count is not calculated and **“—”** is shown. If a dataset has multiple layers, feature counts are summed, and if their CRSs differ, **“Разные”** is shown in the column.

## Format settings

The **“Настройки”** tab lists all supported formats with checkboxes, grouped by category. Checked formats are included in the next scan. Settings are saved between QGIS sessions.

The following quick-selection buttons are available at the top of the tab:

- **“Выбрать все”** — select all formats, including Excel;
- **“Сбросить все”** — clear all selections;
- **“Только вектор”** — keep only vector formats selected;
- **“Только растр”** — keep only raster formats selected.

After a button is clicked, the settings are saved immediately. Changes, like manual checkbox changes, are applied on the next scan.

**Excel** (`.xls`, `.xlsx`) is disabled by default. If enabled, Excel tables will be included in the catalog. After changing the settings, click the refresh button at the top of the panel to rescan the folder.

## File information

The **“Информация”** button is available when exactly one file is selected in the list. For vector data, the dialog shows:

- file name, format, size and full path;
- layer name and coordinate reference system;
- feature count, geometry type, extent and QGIS provider;
- an attribute field table: name, alias, type, length, precision and comment.

For GeoPackage and other multi-layer containers, a layer selector appears at the top of the dialog. For raster files, the CRS, raster dimensions, band count, pixel size and extent are shown.

Below the attribute field table is the **“Экспорт в Excel”** button. It saves the current layer fields to an `.xlsx` file and opens Explorer with the file selected.

## Attribute check

The **“Проверить атрибуты”** button at the bottom of the **“Файлы”** tab iterates over vector files and checks field names. If a field name contains non-Latin characters (for example, Cyrillic), the new **“Проблемы с атрибутами”** column is set to **“Да”**. If the fields contain only Latin characters, digits and common separators, **“Нет”** is shown. For raster files and files without vector fields, **“—”** is shown.

The column appears after the first check. Check progress is shown in the status bar. If the column has already been added, it is also included in the file list export.

After the check finishes, the **“Проблемных файлов: N”** line is shown above the list, and the **“Только проблемные”** checkbox becomes available below the search field. It leaves only files with the **“Да”** value in the table and can be combined with the text filter. If the check was interrupted, the results already obtained are kept, and the counter tooltip shows how many files were processed.

The check can be interrupted with the cancel button next to **“Проверить атрибуты”**. After cancellation, reading characteristics resumes automatically.

## File list export

The **“Экспорт в Excel”** button at the bottom of the **“Файлы”** tab saves the current list to `.xlsx`. The file contains the **“Файл”**, **“Формат”**, **“Система координат”**, **“Элементов”** and **“Размер”** columns. If the **“Проблемы с атрибутами”** column has been added, it is exported as well. If a filter is enabled, only visible rows are exported to the **“Файлы”** worksheet.

A blank row and a total are added at the end of the table: **“Итого файлов: N”**, the total feature count and the total size. If the feature count for some files has not been read yet or is undefined, the total cell shows **“—”**.

A separate **“Статистика”** worksheet is created in the same workbook with the **“Формат”**, **“Кол-во”** and **“Полный объем”** columns. It is built from all found files, like the table on the **“Статистика”** tab, and ends with an **“Итого”** row containing the total file count and size. After a successful save, Windows Explorer opens with the selected `.xlsx` file.

## Full dataset size

The full size of each dataset is calculated automatically together with the CRS and feature count. A separate **“Уточнить”** button is not required. The following sidecar files are included:

- Shapefile: `.shp`, `.dbf`, `.shx`, `.prj`, `.cpg`, `.qix`, `.sbn`, `.sbx`, `.fbn`, `.fbx`, `.ain`, `.aih`, `.atx`, `.ixs`, `.mxs`, `.fix`, `.shp.xml`;
- MapInfo MIF: `.mif` + `.mid`;
- MapInfo TAB: `.tab`, `.dat`, `.map`, `.id`, `.ind`;
- CSV: `.csvt`, `.prj`;
- rasters: world files `.tfw`/`.wld`, `.prj`, `.aux.xml` and `.ovr` (for supported raster formats).

During processing, the status bar shows the number of processed files and the current file name. The size in the table is updated as reading progresses. When finished, the total size in the summary and the **“Статистика”** tab are updated. Row selection and the active filter are preserved.

## Opening in Explorer

The **“Открыть в проводнике”** button is available for one or more selected files. Windows Explorer opens with the file selected. If the selected files are in different folders, a separate Explorer window opens for each folder. If several files in the same folder are selected, the window opens with the first one.

## Statistics

After each scan, two charts and a table are updated on the **“Статистика”** tab:

- **“По размеру”** — the number of files in the ranges up to 1 MB, 1–10 MB, 10–100 MB, 100 MB–1 GB and 1 GB or more. The total size of files in the range is shown on the right.
- **“По типу”** — the number of files by format. The total size is shown on the right; when there are many formats, rare ones are combined into **“Другие форматы”**.
- **“Статистика по форматам”** — a complete table with the **“Формат”**, **“Кол-во”** and **“Полный объем”** columns. Unlike the chart, the table shows each format separately.

The charts and table are built from all found files and do not depend on the list filter. After automatic reading of characteristics, statistics use full dataset sizes including sidecar files.

Below the format table is the **“Экспорт в Excel”** button. The `.xlsx` file contains the **“Формат”**, **“Кол-во”** and **“Полный объем”** columns, and an **“Итого”** row with the total file count and size is added at the end. After saving, Explorer opens with the file selected.

## Supported formats

| Category | Extensions |
|----------|------------|
| Vector | `.shp`, `.gpkg`, `.geojson`, `.json`, `.geojsonl`, `.ndjson`, `.gml`, `.kml`, `.kmz`, `.gpx`, `.tab`, `.mif`, `.dxf`, `.dwg`, `.dgn`, `.fgb`, `.sqlite`, `.spatialite`, `.osm`, `.pbf`, `.parquet`, `.arrow` |
| Raster | `.tif`, `.tiff`, `.cog`, `.img`, `.asc`, `.dem`, `.hgt`, `.jp2`, `.ecw`, `.sid`, `.bil`, `.bsq`, `.bip`, `.nc`, `.hdf`, `.h5`, `.grib`, `.grb`, `.grib2` |
| Tables | `.csv`, `.tsv`, `.xls`, `.xlsx` |
| Other | `.vrt`, `.mbtiles`, `.pmtiles` |

Dataset sidecar files (`.dbf`, `.shx`, `.prj`, `.shp.xml` and similar) are not displayed as separate rows. The extension list is defined in `scanner.py` and is easy to extend.

## Project structure

```text
zgeo/
├── __init__.py          # classFactory entry point
├── README.md            # Russian documentation
├── README_eng.md        # English documentation
├── metadata.txt         # QGIS plugin metadata
├── plugin.py            # toolbar button and panel lifecycle
├── panel.py             # floating panel, file list and statistics tab
├── scanner.py           # scanning, formats and format groups
├── scan_task.py         # background scanning with progress and cancellation
├── dataset_size.py      # full dataset size and sidecar files
├── stats.py             # aggregation by size and format
├── charts.py            # bar charts without external dependencies
├── attribute_check.py   # field name check for non-Latin characters
├── file_info.py         # file, CRS and feature information
├── info_dialog.py       # Information dialog
├── explorer.py          # opening files in Explorer
├── formatting.py        # size formatting
├── excel_export.py      # writing tables to .xlsx without external dependencies
├── table_export.py      # Excel table save dialog
├── icon.svg             # plugin icon
├── img/
│   ├── screen_1.png     # Files tab screenshot
│   ├── screen_2.png     # Statistics tab screenshot
│   └── screen_3.png     # Settings tab screenshot
├── scripts/
│   └── build_zip.ps1    # builds the installation ZIP
└── tests/
    ├── test_scanner.py        # scanner tests
    ├── test_dataset_size.py   # full dataset size
    ├── test_stats.py          # statistics aggregation tests
    ├── test_explorer.py       # grouping files by folder
    ├── test_formatting.py     # size formatting
    ├── test_attribute_check.py # field name check
    └── test_excel_export.py   # XLSX generation
```

## Development

The basic tests do not require QGIS or PyQt:

```powershell
cd zgeo
python -m unittest discover -s tests -t .. -v
```

Syntax check:

```powershell
python -m py_compile __init__.py plugin.py panel.py scanner.py scan_task.py dataset_size.py stats.py charts.py attribute_check.py file_info.py info_dialog.py explorer.py formatting.py excel_export.py table_export.py version.py
```

Scanning runs in a background thread. For very large directories on network drives, the list may fill gradually, but the interface remains responsive and the scan can be interrupted.

---

**Language:** [Русский](README.md) | **English**
