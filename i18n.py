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
    "Проверка атрибутов: {} из {}": "Attribute check: {} of {}",
    "Диаграммы обновятся после завершения поиска файлов.": (
        "Charts will update when the file search finishes."
    ),
    # Вкладки и список файлов
    "Найденные пространственные файлы": "Found spatial files",
    "Диаграммы по размеру и типу файлов": "Charts by file size and type",
    "Форматы файлов, которые нужно искать": "File formats to search for",
    "Фильтр по имени, формату или пути": "Filter by name, format or path",
    "Только проблемные": "Only problem files",
    "Показывать только файлы, у которых проверка атрибутов нашла проблемы": (
        "Show only files with attribute problems"
    ),
    "Открыть в проводнике": "Open in Explorer",
    "Экспорт в Excel": "Export to Excel",
    "Проверить атрибуты": "Check attributes",
    "Прервать длительную операцию": "Cancel long operation",
    "Прервать операцию": "Cancel operation",
    "Прервать проверку атрибутов": "Cancel attribute check",
    "Прервать чтение характеристик": "Cancel reading characteristics",
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
    "Чтение характеристик и объемов: 0 из {}": (
        "Reading characteristics and sizes: 0 of {}"
    ),
    "Чтение характеристик и объемов: {} из {}": (
        "Reading characteristics and sizes: {} of {}"
    ),
    "Чтение характеристик и объемов: {} из {} · {}": (
        "Reading characteristics and sizes: {} of {} · {}"
    ),
    "Чтение характеристик прервано: {} из {}": (
        "Reading characteristics cancelled: {} of {}"
    ),
    "Характеристики и объемы прочитаны. Файлов: {}": (
        "Characteristics and sizes read. Files: {}"
    ),
    "Система координат читается…": "Reading CRS…",
    "Количество элементов читается…": "Reading feature count…",
    "Количество элементов не определено": "Feature count is undefined",
    "Система координат: {}": "CRS: {}",
    "Количество элементов: {}": "Feature count: {}",
    "Полный объем набора: {} Б": "Full dataset size: {} B",
    "{} Б": "{} B",
    "Атрибуты не проверены. Нажмите «Проверить атрибуты».": (
        "Attributes not checked. Click “Check attributes”."
    ),
    "Проверка атрибутов…": "Checking attributes…",
    "Проверка атрибутов выполняется…": "Attribute check in progress…",
    "Проверка атрибутов: 0 из {}": "Attribute check: 0 of {}",
    "Проверка атрибутов: {} из {} · {}": "Attribute check: {} of {} · {}",
    "Проверка атрибутов прервана: обработано {} из {} · проблем {}": (
        "Attribute check cancelled: processed {} of {} · issues {}"
    ),
    "Проверка прервана: обработано {} из {} файлов": (
        "Check cancelled: processed {} of {} files"
    ),
    "Проверить атрибуты: проверить имена полей векторных файлов и добавить колонку «Проблемы с атрибутами».\n"
    "Если в названии поля есть нелатинские символы (например, кириллица) — «Да»; "
    "если проблем нет — «Нет»; для растровых файлов — «—».": (
        "Check attributes: inspect vector field names and add the "
        "“Attribute issues” column.\n"
        "If a field name contains non-Latin characters (for example, "
        "Cyrillic) — “Yes”; if there are no problems — “No”; for raster "
        "files — “—”."
    ),
    "Проверки данных": "Data checks",
    "Выберите проверки": "Select checks",
    "Отметьте проверки, которые нужно выполнить для найденных файлов.": (
        "Select the checks to run on the found files."
    ),
    "Проверка имён атрибутивных полей": "Attribute field name check",
    "Проверяет имена полей векторных файлов и добавляет колонку «Проблемы с атрибутами». Если в имени поля есть нелатинские символы, ставится «Да», иначе «Нет»; для растровых файлов — «—».": (
        "Checks vector field names and adds the “Attribute issues” column. "
        "If a field name contains non-Latin characters, “Yes” is shown; "
        "otherwise “No”; for raster files — “—”."
    ),
    "Уточнение характеристик и объёмов": "Refine characteristics and sizes",
    "Читает систему координат, количество элементов и полный объём наборов данных с учётом сопутствующих файлов.": (
        "Reads the CRS, feature count and full dataset size, including "
        "sidecar files."
    ),
    "Описание проверки: {}": "Check description: {}",
    "Проблемы с атрибутами": "Attribute issues",
    "Да — в именах полей есть нелатинские символы; Нет — проблем не найдено; — — векторных полей нет.": (
        "Yes — field names contain non-Latin characters; No — no problems "
        "found; — — no vector fields."
    ),
    "Векторные атрибутивные поля не найдены.": (
        "No vector attribute fields found."
    ),
    "Идёт проверка атрибутов…": "Attribute check in progress…",
    "Нет векторных файлов для проверки атрибутов": (
        "No vector files to check attributes"
    ),
    "Нелатинские имена полей:\n{}": "Non-Latin field names:\n{}",
    "Проблем с именами полей не найдено.": "No field name problems found.",
    "Атрибуты проверены: файлов {} · с проблемами {}": (
        "Attributes checked: {} files · {} with issues"
    ),
    "Атрибуты проверены: проблем не найдено. Файлов: {}": (
        "Attributes checked: no problems found. Files: {}"
    ),
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
