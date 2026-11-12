"""Минимальная система переводов интерфейса ZGeo.

Строки-исходники в коде остаются на русском языке. Для английского
интерфейса используется словарь ``EN_TRANSLATIONS``. Такой подход не
требует Qt Linguist и позволяет переключать язык без перезапуска QGIS.
"""

from __future__ import annotations

from typing import Any

LANGUAGE_RU = "ru"
LANGUAGE_EN = "en"
DEFAULT_LANGUAGE = LANGUAGE_RU
LANGUAGE_KEY = "zgeo/language"

_current_language = DEFAULT_LANGUAGE

_CATEGORY_SOURCES = {
    "vector": "Векторные данные",
    "raster": "Растровые данные",
    "table": "Таблица",
    "other": "Прочие данные",
}

EN_TRANSLATIONS = {
    # Общие элементы
    "Готово": "Ready",
    "Файл": "File",
    "Файлы": "Files",
    "Формат": "Format",
    "Форматы": "Formats",
    "Статистика": "Statistics",
    "Настройки": "Settings",
    "Информация": "Information",
    "Папка": "Folder",
    "ПАПКА": "FOLDER",
    "Размер": "Size",
    "Элементов": "Features",
    "Система координат": "CRS",
    "Полный объем": "Full size",
    "Кол-во": "Count",
    "Итого": "Total",
    "Данные": "Data",
    "Да": "Yes",
    "Нет": "No",
    "Выполнить": "Run",
    "Отмена": "Cancel",
    "—": "—",
    "…": "…",
    "Б": "B",
    "КБ": "KB",
    "МБ": "MB",
    "ГБ": "GB",
    "ТБ": "TB",
    # Категории и форматы
    "Векторные данные": "Vector data",
    "Растровые данные": "Raster data",
    "Таблица": "Table",
    "Прочие данные": "Other data",
    "Другие форматы": "Other formats",
    # Заголовок и версия
    "ZGeo — геоданные": "ZGeo — geodata",
    "Каталог пространственных данных": "Spatial data catalog",
    "Версия {}": "Version {}",
    "Версия плагина ZGeo: {}": "ZGeo plugin version: {}",
    "неизвестна": "unknown",
    "Переключить язык": "Switch language",
    "Переключить на английский": "Switch to English",
    "Переключить на русский": "Switch to Russian",
    # Выбор папки
    "Папка не выбрана": "No folder selected",
    "Выберите каталог на диске": "Choose a folder on disk",
    "Выбрать папку": "Select folder",
    "Пересканировать папку": "Rescan folder",
    "Выбрать папку с геоданными": "Select a geodata folder",
    "Выбор папки…": "Choosing folder…",
    "Выбор папки отменён": "Folder selection cancelled",
    "Выбранная папка недоступна:\n{}": "The selected folder is unavailable:\n{}",
    # Пустые состояния
    "Геоданные не выбраны": "No geodata selected",
    "Нажмите «Выбрать папку», чтобы найти шейпфайлы, GeoPackage и другие пространственные данные.": (
        "Click “Select folder” to find shapefiles, GeoPackage and other "
        "spatial data."
    ),
    "Статистика пуста": "Statistics is empty",
    "Выберите папку и выполните сканирование. Здесь появятся диаграммы по размеру и типу файлов.": (
        "Select a folder and run a scan. Charts by file size and type will "
        "appear here."
    ),
    "Файлы не найдены": "No files found",
    "В выбранной папке нет поддерживаемых пространственных файлов.": (
        "The selected folder contains no supported spatial files."
    ),
    "После сканирования диаграммы появятся здесь.": (
        "Charts will appear here after scanning."
    ),
    "Нет данных": "No data",
    "Папка недоступна": "Folder unavailable",
    "Каталог был перемещён или удалён. Выберите другую папку.": (
        "The folder was moved or deleted. Choose another folder."
    ),
    "Ничего не найдено": "Nothing found",
    "Измените запрос, снимите фильтр «Только проблемные» или очистите строку фильтра.": (
        "Change the query, clear the “Only problem files” filter, or clear "
        "the filter field."
    ),
    "Сканирование…": "Scanning…",
    "Сканирование папки…": "Scanning folder…",
    "Просматриваем файлы, включая вложенные папки.": (
        "Scanning files, including subfolders."
    ),
    "Имя файла": "File name",
    "Найдено": "Found",
    "Прервать": "Cancel",
    "Диаграммы обновятся после завершения поиска файлов.": (
        "Charts will update when the file search finishes."
    ),
    # Вкладки и список файлов
    "Найденные пространственные файлы": "Found spatial files",
    "Диаграммы по размеру и типу файлов": "Charts by file size and type",
    "Форматы файлов, которые нужно искать": "File formats to search for",
    "Фильтр по имени, формату или пути": "Filter by name, format or path",
    "Только проблемные": "Only problem files",
    "Показывать только файлы, у которых проверки нашли проблемы": (
        "Show only files with problems found by checks"
    ),
    "Открыть в проводнике": "Open in Explorer",
    "Экспорт в Excel": "Export to Excel",
    "Проверки": "Checks",
    "Прервать длительную операцию": "Cancel long operation",
    "Ход выполнения": "Progress",
    "Прервать операцию": "Cancel operation",
    "Прервать проверку атрибутов": "Cancel attribute check",
    "Прервать уточнение данных": "Cancel data refinement",
    "Выбрано: 0 из 0": "Selected: 0 of 0",
    "Выбрано: {} из {}": "Selected: {} of {}",
    "Файлов: 0 · Общий объем: 0 Б": "Files: 0 · Total size: 0 B",
    "Файлов: 0": "Files: 0",
    "Файлов: {}": "Files: {}",
    "{} · Общий объем: {}": "{} · Total size: {}",
    "Показано: {} из {}": "Showing {} of {}",
    "Проблемных файлов: 0": "Problem files: 0",
    "Проблемных файлов: {}": "Problem files: {}",
    "Итого файлов: {}": "Total files: {}",
    # Статусы операций
    "Сканирование… найдено: {}": "Scanning… found: {}",
    "Не удалось прочитать папку": "Could not read folder",
    "Не удалось прочитать папку: {}": "Could not read folder: {}",
    "Сканирование прервано. Найдено: {}": "Scan cancelled. Found: {}",
    "Сканирование завершено. Найдено: {}": "Scan completed. Found: {}",
    "Прервано · найдено: {}": "Cancelled · found: {}",
    "Прервано · найдено: 0": "Cancelled · found: 0",
    "Сканирование прервано": "Scan cancelled",
    "Поиск остановлен пользователем. Поддерживаемые файлы не найдены.": (
        "Search stopped by user. No supported files found."
    ),
    "Поиск остановлен пользователем.": "Search stopped by user.",
    "Прерывание…": "Cancelling…",
    "Прерывание сканирования…": "Cancelling scan…",
    "Уточнение данных": "Data refinement",
    "Уточнение размера": "Size refinement",
    "Уточнение размера SHP": "SHP size refinement",
    "Уточнение размера MIF/MID": "MIF/MID size refinement",
    "Уточнение системы координат": "CRS refinement",
    "Уточнение количества элементов": "Feature count refinement",
    "{}: 0 из {}": "{}: 0 of {}",
    "{}: {} из {}": "{}: {} of {}",
    "{}: {} из {} · {}": "{}: {} of {} · {}",
    "{} завершено. Файлов: {}": "{} completed. Files: {}",
    "{} прервано: {} из {}": "{} cancelled: {} of {}",
    "Нет файлов для выбранных проверок": (
        "No files for the selected checks"
    ),
    "Система координат читается…": "Reading CRS…",
    "Количество элементов читается…": "Reading feature count…",
    "Количество элементов не определено": "Feature count is undefined",
    "Система координат не определена": "CRS is undefined",
    "Система координат: {}": "CRS: {}",
    "Количество элементов: {}": "Feature count: {}",
    "Полный объем набора: {} Б": "Full dataset size: {} B",
    "{} Б": "{} B",
    "Система координат не уточнена. Нажмите «Проверки».": (
        "CRS not refined. Click “Checks”."
    ),
    "Количество элементов не уточнено. Нажмите «Проверки».": (
        "Feature count not refined. Click “Checks”."
    ),
    "Размер основного файла: {} Б. Нажмите «Проверки», чтобы уточнить полный размер.": (
        "Main file size: {} B. Click “Checks” to refine the full size."
    ),
    "Проверки не выполнялись. Нажмите «Проверки».": (
        "Checks have not been run. Click “Checks”."
    ),
    "Проверка выполняется…": "Checking…",
    "Проверки выполняются…": "Checks are running…",
    "Проверки: 0 из {}": "Checks: 0 of {}",
    "Проверки: {} из {}": "Checks: {} of {}",
    "Проверки: {} из {} · {}": "Checks: {} of {} · {}",
    "Проверки завершены: файлов {} · с проблемами {}": (
        "Checks completed: {} files · {} with issues"
    ),
    "Проверки завершены: проблем не найдено. Файлов: {}": (
        "Checks completed: no problems found. Files: {}"
    ),
    "Проверки прерваны: обработано {} из {} · проблем {}": (
        "Checks cancelled: processed {} of {} · issues {}"
    ),
    "Проверка прервана: обработано {} из {} файлов": (
        "Check cancelled: processed {} of {} files"
    ),
    "Проверка не применима к этому файлу.": (
        "Check is not applicable to this file."
    ),
    "Проблем не найдено.": "No problems found.",
    "Идёт проверка…": "Check in progress…",
    "Прервать проверки": "Cancel checks",
    "Проверки: уточнить размер (в том числе отдельно для SHP и MIF/MID), систему координат и количество элементов, проверить JSON, имена полей, набор данных, геометрии и координаты.": (
        "Checks: refine size (including separately for SHP and MIF/MID), "
        "CRS and feature count, validate JSON, field names, dataset "
        "integrity, geometries and coordinates."
    ),
    "Выберите проверки": "Select checks",
    "Отметьте проверки, которые нужно выполнить для найденных файлов.": (
        "Select the checks to run on the found files."
    ),
    "Уточнить размер": "Refine size",
    "Считает полный размер каждого набора данных с учётом сопутствующих файлов.": (
        "Calculates the full size of each dataset, including sidecar files."
    ),
    "Уточнить размер SHP": "Refine SHP size",
    "Считает полный размер только наборов ESRI Shapefile с учётом сопутствующих файлов.": (
        "Calculates the full size of ESRI Shapefile datasets only, including "
        "sidecar files."
    ),
    "Уточнить размер MIF/MID": "Refine MIF/MID size",
    "Считает полный размер только наборов MapInfo MIF/MID с учётом файлов .mif и .mid.": (
        "Calculates the full size of MapInfo MIF/MID datasets only, "
        "including the .mif and .mid files."
    ),
    "Уточнить систему координат": "Refine CRS",
    "Читает систему координат слоёв и обновляет колонку «Система координат».": (
        "Reads the CRS of layers and updates the “CRS” column."
    ),
    "Уточнить количество элементов": "Refine feature count",
    "Считает количество элементов слоёв и обновляет колонку «Элементов».": (
        "Counts layer features and updates the “Features” column."
    ),
    "Проверка JSON на формат GEOJSON": "Check JSON for GeoJSON format",
    "Проверяет файлы .json и .geojson по полю type. Файлы, не являющиеся GeoJSON, исключаются из списка.": (
        "Checks .json and .geojson files by the type field. Files that are "
        "not GeoJSON are excluded from the list."
    ),
    "Проверка JSON на формат GeoJSON: 0 из {}": (
        "JSON check for GeoJSON format: 0 of {}"
    ),
    "Проверка JSON: {} из {} · {}": "JSON check: {} of {} · {}",
    "Проверка JSON завершена: проверено {} · исключено {}": (
        "JSON check completed: checked {} · excluded {}"
    ),
    "Проверка JSON завершена: все файлы соответствуют GeoJSON. Проверено: {}": (
        "JSON check completed: all files are GeoJSON. Checked: {}"
    ),
    "Проверка JSON прервана: проверено {} из {} · исключено {}": (
        "JSON check cancelled: checked {} of {} · excluded {}"
    ),
    "Проверка JSON выполняется…": "JSON check in progress…",
    "Прервать проверку JSON": "Cancel JSON check",
    "Нет JSON-файлов для проверки": "No JSON files to check",
    "Все найденные файлы исключены проверками.": (
        "All found files were excluded by checks."
    ),
    "Нет файлов для построения диаграмм.": "No files to build charts.",
    "Проверка имён атрибутивных полей": "Attribute field name check",
    "Проверяет имена полей векторных файлов на нелатинские символы и добавляет колонку «Проблемы». Если в имени поля есть нелатинские символы, ставится «Да», иначе «Нет»; для растровых файлов — «—».": (
        "Checks vector field names for non-Latin characters and adds the "
        "“Issues” column. If a field name contains non-Latin characters, "
        "“Yes” is shown; otherwise “No”; for raster files — “—”."
    ),
    "Проверка имён полей для Shapefile": "Shapefile field name check",
    "Проверяет длину имён полей (не более 10 символов для DBF), пробелы и недопустимые символы.": (
        "Checks field name length (10 characters max for DBF), spaces and "
        "invalid characters."
    ),
    "Проверка дублей имён после усечения": (
        "Truncated field name duplicates check"
    ),
    "Ищет поля, имена которых совпадают после усечения до 10 символов.": (
        "Finds fields whose names collide after truncation to 10 characters."
    ),
    "Проверка кодировки DBF и .cpg": "DBF encoding and .cpg check",
    "Проверяет наличие файла .cpg и корректность указанной кодировки DBF.": (
        "Checks for the .cpg file and validates the specified DBF encoding."
    ),
    "Проверка комплектности набора": "Dataset completeness check",
    "Проверяет обязательные файлы: .shp + .dbf + .shx, .mif + .mid, .tab + .dat/.map/.id.": (
        "Checks required files: .shp + .dbf + .shx, .mif + .mid, "
        ".tab + .dat/.map/.id."
    ),
    "Проверка системы координат": "CRS check",
    "Ищет файлы без системы координат, с неизвестной или смешанной системой координат.": (
        "Finds files without a CRS, with an unknown CRS or with mixed CRSs."
    ),
    "Проверка валидности геометрий": "Geometry validity check",
    "Ищет самопересечения, незамкнутые кольца, пустые и null-геометрии.": (
        "Finds self-intersections, unclosed rings, empty and null geometries."
    ),
    "Проверка координат": "Coordinate check",
    "Ищет NaN/Inf, слишком большие координаты, перепутанные широту и долготу и выход за допустимый диапазон CRS.": (
        "Finds NaN/Inf, excessively large coordinates, swapped latitude "
        "and longitude, and coordinates outside the valid CRS range."
    ),
    "Проверка пустых слоёв": "Empty layers check",
    "Ищет пустые слои и файлы с нулевым количеством объектов.": (
        "Finds empty layers and files with zero features."
    ),
    "Описание проверки: {}": "Check description: {}",
    "Проблемы": "Issues",
    "Да — найдены проблемы; Нет — проблем не найдено; — — проверка не применима.": (
        "Yes — problems found; No — no problems found; — — check is not "
        "applicable."
    ),
    "Нелатинские имена полей:\n{}": "Non-Latin field names:\n{}",
    "В наборе отсутствуют файлы: {}": "Dataset is missing files: {}",
    "Не удалось прочитать заголовок DBF": (
        "Could not read the DBF header"
    ),
    "Нет файла .cpg: кодировка DBF не указана": (
        "No .cpg file: DBF encoding is not specified"
    ),
    "Файл .cpg пуст: кодировка DBF не указана": (
        "The .cpg file is empty: DBF encoding is not specified"
    ),
    "Неизвестная кодировка в .cpg: {}": "Unknown encoding in .cpg: {}",
    "Поле «{}»: длина {} больше {} символов (ограничение DBF)": (
        "Field “{}”: length {} exceeds {} characters (DBF limit)"
    ),
    "Поле «{}»: содержит пробел": "Field “{}”: contains a space",
    "Поле «{}»: недопустимые символы: {}": (
        "Field “{}”: invalid characters: {}"
    ),
    "Слой «{}»: после усечения до {} символов совпадают имена полей: {}": (
        "Layer “{}”: field names collide after truncation to {} characters: "
        "{}"
    ),
    "У части слоёв не определена система координат": (
        "Some layers have no CRS"
    ),
    "Смешанные системы координат: {}": "Mixed CRS: {}",
    "Слой «{}»: некорректных геометрий: {} (самопересечения: {}, незамкнутые кольца: {}, прочие: {}), пустых: {}, null-геометрий: {}": (
        "Layer “{}”: invalid geometries: {} (self-intersections: {}, "
        "unclosed rings: {}, other: {}), empty: {}, null geometries: {}"
    ),
    "Слой «{}»: координаты — NaN/Inf: {}, слишком большие: {}, вне диапазона CRS: {}, похоже на перепутанные широту и долготу: {}": (
        "Layer “{}”: coordinates — NaN/Inf: {}, excessively large: {}, "
        "outside CRS range: {}, possibly swapped latitude and longitude: {}"
    ),
    "Файл не содержит объектов": "File contains no features",
    "Слой «{}» не содержит объектов": "Layer “{}” contains no features",
    "Уточнить систему координат и проверить СК": (
        "Refine CRS and check it"
    ),
    "Читает систему координат слоёв, обновляет колонку «Система координат» и отмечает отсутствующую, неизвестную или смешанную СК.": (
        "Reads the CRS of layers, updates the “CRS” column and flags "
        "missing, unknown or mixed CRS."
    ),
    "Уточнить количество элементов и проверить пустые слои": (
        "Refine feature count and check empty layers"
    ),
    "Считает количество элементов, обновляет колонку «Элементов» и отмечает пустые слои и файлы без объектов.": (
        "Counts features, updates the “Features” column and flags empty "
        "layers and files without features."
    ),
    "Проверка имён полей": "Field name check",
    "Проверяет нелатинские символы, длину имени (не более 10 символов DBF), пробелы, недопустимые символы и дубли после усечения.": (
        "Checks non-Latin characters, name length (10 characters max for "
        "DBF), spaces, invalid characters and duplicates after truncation."
    ),
    "Проверка набора данных": "Dataset integrity check",
    "Проверяет обязательные файлы набора, наличие .cpg и корректность указанной кодировки DBF.": (
        "Checks required dataset files, the presence of .cpg and the "
        "specified DBF encoding."
    ),
    "Проверка геометрий и координат": "Geometry and coordinate check",
    "Ищет самопересечения, незамкнутые кольца, пустые и null-геометрии, NaN/Inf, слишком большие координаты, перепутанные широту и долготу и выход за диапазон CRS.": (
        "Finds self-intersections, unclosed rings, empty and null "
        "geometries, NaN/Inf, excessively large coordinates, swapped "
        "latitude and longitude, and coordinates outside the CRS range."
    ),
    "Нелатинское имя поля: {}": "Non-Latin field name: {}",
    "Геометрия отсутствует (null)": "Geometry is missing (null)",
    "Пустая геометрия": "Empty geometry",
    "Незамкнутое кольцо": "Unclosed ring",
    "Самопересечение": "Self-intersection",
    "Некорректная геометрия: {}": "Invalid geometry: {}",
    "Не удалось проверить геометрию": "Could not validate geometry",
    "Координата NaN/Inf": "NaN/Inf coordinate",
    "Слишком большая координата": "Excessively large coordinate",
    "Похоже на перепутанные широту и долготу": (
        "Possibly swapped latitude and longitude"
    ),
    "Координата вне диапазона CRS": "Coordinate outside the CRS range",
    "Вершина {}": "Vertex {}",
    "Полный путь": "Full path",
    "Идентификатор объекта": "Feature ID",
    "Где ошибка": "Where",
    "Описание ошибки": "Error description",
    "Статистика проверок": "Check statistics",
    "Проверка": "Check",
    "Файлов с проблемами": "Files with issues",
    "Ошибок": "Issues",
    "Проверки: {}": "Checks: {}",
    "Текущая проверка": "Current check",
    # Информация о файле
    "Информация — {}": "Information — {}",
    "Слой:": "Layer:",
    "Не удалось получить пространственные сведения. Файл может быть повреждён или его формат не поддерживается установленными провайдерами QGIS.": (
        "Could not retrieve spatial information. The file may be corrupted "
        "or its format is not supported by the installed QGIS providers."
    ),
    "Вектор · {}": "Vector · {}",
    "Растр · {}": "Raster · {}",
    "Слой": "Layer",
    "Количество объектов": "Feature count",
    "Геометрия": "Geometry",
    "Экстент": "Extent",
    "Провайдер": "Provider",
    "Атрибутивные поля ({})": "Attribute fields ({})",
    "Атрибутивные поля отсутствуют.": "No attribute fields.",
    "Атрибутивные поля": "Attribute fields",
    "{}_поля.xlsx": "{}_fields.xlsx",
    "Размер растра": "Raster size",
    "Количество каналов": "Band count",
    "Размер пикселя": "Pixel size",
    "Имя": "Name",
    "Алиас": "Alias",
    "Тип": "Type",
    "Длина": "Length",
    "Точность": "Precision",
    "Комментарий": "Comment",
    "Недоступно": "Unavailable",
    # Статистика
    "По размеру": "By size",
    "По типу": "By type",
    "Статистика по форматам": "Statistics by format",
    "Диаграммы построены по всем найденным файлам.": (
        "Charts are built from all found files."
    ),
    "Количество файлов в диапазонах размера; справа — суммарный объём.": (
        "Number of files in size ranges; total size on the right."
    ),
    "Количество файлов по формату; справа — суммарный объём. Показаны основные форматы, остальные объединены в «Другие форматы».": (
        "Number of files by format; total size on the right. Main formats "
        "are shown, the rest are grouped as “Other formats”."
    ),
    "Полная статистика по каждому формату. Объём учитывает сопутствующие файлы наборов данных.": (
        "Complete statistics for each format. Size includes dataset sidecar "
        "files."
    ),
    "Файлов: {} · {}": "Files: {} · {}",
    "{}: {} файлов ({:.0f}%), {}": "{}: {} files ({:.0f}%), {}",
    "Экспорт статистики в Excel…": "Exporting statistics to Excel…",
    "{}_форматы.xlsx": "{}_formats.xlsx",
    "Статистика экспортирована: {}": "Statistics exported: {}",
    "Экспорт статистики отменён": "Statistics export cancelled",
    "Файлов: 0 · 0 Б": "Files: 0 · 0 B",
    "Экспорт списка в Excel…": "Exporting list to Excel…",
    "{}_файлы.xlsx": "{}_files.xlsx",
    "Список экспортирован: {}": "List exported: {}",
    "Экспорт списка отменён": "List export cancelled",
    # Диаграммы
    "Столбчатая диаграмма": "Bar chart",
    "Диаграмма по размеру": "Chart by size",
    "Диаграмма по типу": "Chart by type",
    # Форматирование
    "До 1 МБ": "Up to 1 MB",
    "1–10 МБ": "1–10 MB",
    "10–100 МБ": "10–100 MB",
    "100 МБ–1 ГБ": "100 MB–1 GB",
    "1 ГБ и более": "1 GB and more",
    # Диалог экспорта
    "Не удалось экспортировать таблицу:\n{}": (
        "Could not export the table:\n{}"
    ),
    "Таблица экспортирована:\n{}\n\nНе удалось открыть проводник:\n{}": (
        "Table exported:\n{}\n\nCould not open Explorer:\n{}"
    ),
    # Сообщения о файлах
    "Векторные данные: {}": "Vector data: {}",
    "Растровые данные: {}": "Raster data: {}",
    "Разные": "Mixed",
    "Не определена": "Undefined",
    "Без геометрии": "No geometry",
    # Действия и статусы
    "Фильтр: показано {} из {}": "Filter: showing {} of {}",
    "Фильтр «Только проблемные»: показано {} из {}": (
        "Filter “Only problem files”: showing {} of {}"
    ),
    "Фильтр очищен": "Filter cleared",
    "Получение информации: {}": "Getting information: {}",
    "Не удалось получить информацию: {}": "Could not get information: {}",
    "Не удалось получить информацию о файле:\n{}": (
        "Could not get file information:\n{}"
    ),
    "Информация: {}": "Information: {}",
    "Открываю проводник: {}": "Opening Explorer: {}",
    "Не удалось открыть проводник": "Could not open Explorer",
    "Не удалось открыть проводник:\n\n{}": (
        "Could not open Explorer:\n\n{}"
    ),
    "Проводник открыт: {}": "Explorer opened: {}",
    # Настройки
    "Выбрать все": "Select all",
    "Отметить все форматы": "Select all formats",
    "Сбросить все": "Clear all",
    "Снять все отметки": "Clear all selections",
    "Только вектор": "Vector only",
    "Оставить только векторные форматы": "Keep only vector formats",
    "Только растр": "Raster only",
    "Оставить только растровые форматы": "Keep only raster formats",
    "Отметьте форматы, которые должны попадать в каталог. Изменения применяются при следующем сканировании.": (
        "Select the formats to include in the catalog. Changes apply on the "
        "next scan."
    ),
    "Расширения: {}": "Extensions: {}",
    "Настройки сохранены. Изменения применятся при следующем сканировании.": (
        "Settings saved. Changes will apply on the next scan."
    ),
    "Все форматы выбраны. Изменения применятся при следующем сканировании.": (
        "All formats selected. Changes will apply on the next scan."
    ),
    "Все форматы сброшены. Изменения применятся при следующем сканировании.": (
        "All formats cleared. Changes will apply on the next scan."
    ),
    "Выбраны только векторные форматы. Изменения применятся при следующем сканировании.": (
        "Only vector formats selected. Changes will apply on the next scan."
    ),
    "Выбраны только растровые форматы. Изменения применятся при следующем сканировании.": (
        "Only raster formats selected. Changes will apply on the next scan."
    ),
    # QGIS
    "ZGeo-Каталог": "ZGeo Catalog",
    "ZGeo-Каталог — каталог пространственных данных": (
        "ZGeo Catalog — spatial data catalog"
    ),
    "Открыть плавающую панель ZGeo-Каталог": (
        "Open the floating ZGeo Catalog panel"
    ),
}


def normalize_language(value: Any) -> str:
    """Привести значение настройки к поддерживаемому коду языка."""

    text = str(value or "").strip().lower()
    if text.startswith(LANGUAGE_EN):
        return LANGUAGE_EN
    return LANGUAGE_RU


def get_language() -> str:
    """Вернуть текущий язык интерфейса."""

    return _current_language


def set_language(value: Any) -> str:
    """Установить язык интерфейса и вернуть его код."""

    global _current_language
    _current_language = normalize_language(value)
    return _current_language


def tr(text: str, *args: Any, **kwargs: Any) -> str:
    """Перевести строку и при необходимости подставить параметры."""

    translated = (
        EN_TRANSLATIONS.get(text, text)
        if _current_language == LANGUAGE_EN
        else text
    )
    if args or kwargs:
        return translated.format(*args, **kwargs)
    return translated


def category_label(category: str) -> str:
    """Вернуть переведённую подпись категории форматов."""

    return tr(_CATEGORY_SOURCES.get(category, category))
