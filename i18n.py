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
    "Путь": "Path",
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
    "Добавить в текущий проект": "Add to current project",
    "Добавить выбранные файлы слоями в текущий проект": (
        "Add the selected files as layers to the current project"
    ),
    "Добавляю файлы в проект: {}": "Adding files to the project: {}",
    "Добавлено слоёв в проект: {}": "Layers added to the project: {}",
    "Слои уже есть в проекте: {}": (
        "The layers are already in the project: {}"
    ),
    "Добавлено слоёв в проект: {} · уже есть: {}": (
        "Layers added to the project: {} · already present: {}"
    ),
    "Не удалось добавить слои:\n\n{}": (
        "Could not add layers:\n\n{}"
    ),
    "Нечего добавлять: выбранные файлы не открылись": (
        "Nothing to add: the selected files could not be opened"
    ),

    "Скопировать в …": "Copy to …",
    "Скопировать выбранные файлы и сопутствующие файлы в папку": (
        "Copy selected files and sidecar files to a folder"
    ),
    "Выберите папку для копирования": "Select a destination folder",
    "Копирование файлов…": "Copying files…",
    "Копирование: {}\n{} из {}": "Copying: {}\n{} of {}",
    "Копирование отменено": "Copy cancelled",
    "Копирование отменено: {} из {}": "Copy cancelled: {} of {}",
    "Файлы уже находятся в выбранной папке": (
        "The files are already in the selected folder"
    ),
    "В выбранных файлах есть совпадающие имена:\n{}\n\nСкопируйте их по отдельности.": (
        "The selected files contain duplicate names:\n{}\n\n"
        "Copy them separately."
    ),
    "В папке назначения уже есть файлы:\n{}\n\nЗаменить их?": (
        "The destination folder already contains files:\n{}\n\n"
        "Replace them?"
    ),
    "Не удалось скопировать файлы:\n\n{}": (
        "Could not copy files:\n\n{}"
    ),
    "Не удалось открыть папку:\n\n{}": (
        "Could not open the folder:\n\n{}"
    ),
    "Скопировано файлов: {}": "Files copied: {}",
    "Скопировано файлов: {}; ошибок: {}": (
        "Files copied: {}; errors: {}"
    ),
    "Экспорт": "Export",
    "Экспорт в Excel": "Export to Excel",
    "Экспорт в HTML": "Export to HTML",
    "Экспортировать список в Excel или HTML": (
        "Export the list to Excel or HTML"
    ),
    "Проверки": "Checks",
    "Качество пространственных данных": "Spatial data quality",
    "Качество атрибутивных данных": "Attribute data quality",
    "Проверки геометрии, системы координат, файлов и наборов данных.": (
        "Checks for geometry, CRS, files and datasets."
    ),
    "Проверки имён полей, дублей имён и заполненности атрибутов.": (
        "Checks for field names, duplicate names and attribute "
        "completeness."
    ),
    "Выполнить выбранные проверки": "Run selected checks",
    "По умолчанию": "Defaults",
    "Управляющие и невидимые символы": "Control and invisible characters",
    "Дубли по атрибутам (очень долго!)": "Attribute duplicates (very slow!)",
    "Пустые строки": "Blank strings",
    "Пробелы по краям значений": "Leading and trailing spaces",
    "Двойные пробелы внутри значений": "Double spaces inside values",
    "Числа, записанные как текст": "Numbers stored as text",
    "Аномальная длина текста": "Abnormal text length",
    "Даты вне разумного диапазона": "Dates outside a reasonable range",
    "Подозрительные имена полей": "Suspicious field names",
    "Ищет технические имена после импорта и имена, "
    "обозначающие отсутствующее значение.": (
        "Looks for technical names produced by an import and names that "
        "mean a missing value."
    ),
    "ZGeo читает имена полей каждого векторного слоя и "
    "отмечает пустое имя, имена, обозначающие отсутствие "
    "значения (NULL, None, NaN, Nil, Undefined), имена из "
    "одних цифр и технические имена после импорта: Field1, "
    "field_2, Column3, Unnamed: 0, Attribute1.": (
        "ZGeo reads the field names of every vector layer and flags an empty "
        "name, names that mean a missing value (NULL, None, NaN, Nil, "
        "Undefined), names made of digits only and technical names produced "
        "by an import: Field1, field_2, Column3, Unnamed: 0, Attribute1."
    ),
    "Такие имена появляются при импорте таблиц и текстовых "
    "файлов без заголовков, при склейке источников и после "
    "конвертации из Excel. В справочнике их нет, поэтому "
    "слой нельзя сопоставить с эталонной схемой, а отчёты "
    "и подписи получают бессмысленные заголовки.": (
        "Such names appear when tables and text files without headers are "
        "imported, when sources are concatenated and after a conversion from "
        "Excel. They are not in the dictionary, so the layer cannot be "
        "matched to the reference schema and reports and labels get "
        "meaningless headings."
    ),
    "Осмысленные короткие имена (id, code, name, OBJECTID) "
    "проблемой не считаются. Проверка только сообщает о "
    "проблемах и не переименовывает поля.": (
        "Meaningful short names (id, code, name, OBJECTID) are not reported. "
        "The check only reports problems and does not rename fields."
    ),
    "Поле Field1 — техническое имя после импорта.": (
        "The field Field1 — a technical name produced by an import."
    ),
    "Поле NULL — имя обозначает отсутствующее значение.": (
        "The field NULL — the name means a missing value."
    ),
    "Поле 2024 — имя состоит только из цифр.": (
        "The field 2024 — the name is made of digits only."
    ),
    "Поля OBJECTID и name — проблемы нет.": (
        "The fields OBJECTID and name — no problem."
    ),
    "Слой «{}»: подозрительное имя поля «{}» — {}": (
        "Layer \"{}\": suspicious field name \"{}\" — {}"
    ),
    "имя обозначает отсутствующее значение": (
        "the name means a missing value"
    ),
    "имя состоит только из цифр": "the name is made of digits only",
    "техническое имя после импорта": (
        "a technical name produced by an import"
    ),
    "имя поля пустое": "the field name is empty",

    "Ищет даты и отметки времени раньше 1900 года и позже "
    "текущего года.": (
        "Looks for dates and timestamps earlier than 1900 and later than "
        "the current year."
    ),
    "ZGeo читает поля дат, отметок времени и текстовые "
    "поля, разбирает значения как дату и отмечает годы "
    "раньше 1900 и позже текущего года.": (
        "ZGeo reads date, timestamp and text fields, parses the values as "
        "dates and flags years earlier than 1900 and later than the current "
        "year."
    ),
    "Поддерживаются записи ГГГГ-ММ-ДД, ДД.ММ.ГГГГ, "
    "ДД/ММ/ГГГГ и ГГГГ/ММ/ДД, в том числе с временем "
    "через «T» или пробел. Нулевая дата вида 0000-00-00 "
    "тоже отмечается.": (
        "The formats YYYY-MM-DD, DD.MM.YYYY, DD/MM/YYYY and YYYY/MM/DD are "
        "supported, including a time part after \"T\" or a space. The zero "
        "date 0000-00-00 is reported as well."
    ),
    "Так выглядят даты, записанные в неверном формате, и "
    "результат подстановки нулевой даты. Такие значения "
    "ломают временные фильтры и хронологию в отчётах: "
    "сортировка по дате ставит их в начало или в конец "
    "списка.": (
        "This is how dates written in a wrong format and the result of a "
        "zero-date substitution look. Such values break time filters and the "
        "chronology in reports: sorting by date puts them at the beginning "
        "or at the end of the list."
    ),
    "В отчёте по каждому полю показываются число объектов, "
    "доля, минимальный и максимальный найденный год, "
    "объекты и сами значения.": (
        "For every field the report shows the number of features, the "
        "share, the minimum and maximum year found, the features and the "
        "values themselves."
    ),
    "Значение 1899-12-30 — отмечается как дата раньше "
    "1900 года.": (
        "The value 1899-12-30 — reported as a date earlier than 1900."
    ),
    "Значение 0000-00-00 — отмечается нулевая дата.": (
        "The value 0000-00-00 — the zero date is reported."
    ),
    "Значение 2999-01-01 — отмечается как дата позже "
    "текущего года.": (
        "The value 2999-01-01 — reported as a date later than the current "
        "year."
    ),
    "Значение 2024-05-01 — проблемы нет.": (
        "The value 2024-05-01 — no problem."
    ),
    "Слой «{}»: даты вне разумного диапазона — "
    "затронуто полей {} из {}: {}": (
        "Layer \"{}\": dates outside a reasonable range — {} of {} fields "
        "affected: {}"
    ),
    "Поле «{}»: даты вне разумного диапазона у {} из {} "
    "объектов ({}%); годы от {} до {} (объекты: {}); "
    "значения: {}": (
        "Field \"{}\": dates outside a reasonable range in {} of {} "
        "features ({}%); years from {} to {} (features: {}); values: {}"
    ),

    "Считает среднюю длину значения и стандартное отклонение "
    "и ищет значения длиннее среднего более чем на три "
    "отклонения.": (
        "Computes the average value length and the standard deviation and "
        "looks for values longer than the average by more than three "
        "deviations."
    ),
    "Для каждого текстового поля ZGeo считает длину "
    "каждого непустого значения, среднюю длину и "
    "стандартное отклонение, а затем отмечает значения "
    "длиннее среднего более чем на три отклонения.": (
        "For every text field ZGeo measures the length of each non-empty "
        "value, computes the average length and the standard deviation, and "
        "then flags values longer than the average by more than three "
        "deviations."
    ),
    "Так находятся обрезанные поля справочника и, "
    "наоборот, значения со склеенным или лишним текстом: "
    "в поле из двух-трёх слов появляется целая строка "
    "адреса или несколько значений через разделитель.": (
        "This finds truncated dictionary fields and, conversely, values with "
        "concatenated or extra text: a field of two or three words suddenly "
        "contains a full address line or several values separated by a "
        "delimiter."
    ),
    "Проверка работает только по длине и не читает "
    "содержимое, поэтому подсказка показывает среднее, "
    "отклонение, самую длинную длину и пример значения. "
    "Для полей с малым числом значений (меньше трёх) и с "
    "одинаковой длиной всех значений проверка ничего не "
    "отмечает.": (
        "The check works on lengths only and does not read the content, so "
        "the tooltip shows the average, the deviation, the longest length "
        "and a sample value. Fields with few values (fewer than three) and "
        "fields where every value has the same length produce no findings."
    ),
    "Поле name со значениями «Москва», «Тверь», «Омск» и "
    "одним значением «Москва, Тверь, Омск, Тула, Сочи» — "
    "отмечается одно аномальное значение.": (
        "The name field with the values \"Москва\", \"Тверь\", "
        "\"Омск\" and one value \"Москва, Тверь, Омск, Тула, Сочи\" — "
        "one abnormal value is reported."
    ),
    "Поле code со значениями одинаковой длины — проблем "
    "нет.": (
        "The code field with values of the same length — no problems."
    ),
    "Поле из двух значений — проверка не применяется, "
    "статистики слишком мало.": (
        "A field with two values — the check does not apply, there is too "
        "little statistics."
    ),
    "Слой «{}»: аномальная длина текста — "
    "затронуто полей {} из {}: {}": (
        "Layer \"{}\": abnormal text length — {} of {} fields affected: {}"
    ),
    "Поле «{}»: значения аномальной длины у {} из {} "
    "объектов ({}%); среднее {}, отклонение {}, самая длинная "
    "{} символов (объекты: {})": (
        "Field \"{}\": abnormal length values in {} of {} features ({}%); "
        "average {}, deviation {}, longest {} characters (features: {})"
    ),
    "Поле «{}»: значения аномальной длины у {} из {} "
    "объектов ({}%); среднее {}, отклонение {}, самая длинная "
    "{} символов (объекты: {}); пример: {}": (
        "Field \"{}\": abnormal length values in {} of {} features ({}%); "
        "average {}, deviation {}, longest {} characters (features: {}); "
        "sample: {}"
    ),

    "Ищет текстовые столбцы, где значения являются числами: "
    "идентификаторы, площади, коды.": (
        "Looks for text columns whose values are numbers: identifiers, "
        "areas, codes."
    ),
    "Для каждого векторного слоя и таблицы ZGeo читает "
    "текстовые поля и проверяет значения: число состоит из "
    "цифр, не более чем одного десятичного разделителя "
    "(точки или запятой), знака и экспоненты. Пробелы "
    "внутри значения, буквы и повторные разделители "
    "делают значение нечисловым.": (
        "For every vector layer and table ZGeo reads the text fields and "
        "checks the values: a number consists of digits, at most one "
        "decimal separator (a dot or a comma), a sign and an exponent. "
        "Spaces inside the value, letters and repeated separators make the "
        "value non-numeric."
    ),
    "Обычно так выглядят поля, которые нужно хранить "
    "числом: идентификаторы, площади, коды. Из-за "
    "текстового типа сравнение идёт по алфавиту («10» "
    "меньше «9») и невозможны арифметические операции.": (
        "This is how fields that should be stored as numbers usually look: "
        "identifiers, areas, codes. Because of the text type the comparison "
        "is alphabetical (\"10\" is less than \"9\") and arithmetic "
        "operations are impossible."
    ),
    "В отчёте по каждому полю показывается число объектов, "
    "доля, сколько значений целых и сколько дробных, и "
    "пример значения. Ведущие нули не мешают: «007» тоже "
    "считается числом, записанным как текст.": (
        "For every field the report shows the number of features, the "
        "share, how many values are integer and how many are real, and a "
        "sample value. Leading zeros do not matter: \"007\" also counts "
        "as a number stored as text."
    ),
    "Поле code типа «текст» со значениями «10», «9», «007» "
    "— отмечается 3 числа, записанных как текст.": (
        "A text field code with the values \"10\", \"9\", \"007\" — "
        "3 numbers stored as text are reported."
    ),
    "Поле area со значениями «12.5» и «7» — отмечается "
    "два числа, одно дробное.": (
        "The field area with the values \"12.5\" and \"7\" — two "
        "numbers are reported, one of them real."
    ),
    "Значение «12a» или «1 234» — числом не считается.": (
        "The value \"12a\" or \"1 234\" does not count as a number."
    ),
    "Слой «{}»: числа, записанные как текст — "
    "затронуто полей {} из {}: {}": (
        "Layer \"{}\": numbers stored as text — {} of {} fields "
        "affected: {}"
    ),
    "Поле «{}»: числа, записанные как текст, у {} из {} "
    "объектов ({}%); целых {}, дробных {}": (
        "Field \"{}\": numbers stored as text in {} of {} features "
        "({}%); integer {}, real {}"
    ),
    "Поле «{}»: числа, записанные как текст, у {} из {} "
    "объектов ({}%); целых {}, дробных {}; пример: «{}»": (
        "Field \"{}\": numbers stored as text in {} of {} features "
        "({}%); integer {}, real {}; sample: \"{}\""
    ),

    "Ищет значения, внутри которых стоят два и более "
    "пробела подряд.": (
        "Looks for values containing two or more consecutive spaces."
    ),
    "Для каждого векторного слоя и таблицы ZGeo читает "
    "текстовые поля, отбрасывает пробелы по краям и ищет "
    "внутри значения последовательности из двух и более "
    "пробельных символов подряд.": (
        "For every vector layer and table ZGeo reads the text fields, trims "
        "the edge spaces and looks for runs of two or more whitespace "
        "characters inside the value."
    ),
    "Обычно это следствие ручного ввода или склейки полей. "
    "Такие записи не находятся поиском по точному значению "
    "и выглядят неряшливо в отчётах, а сравнение с "
    "нормализованным значением даёт ложное несовпадение.": (
        "This is usually the result of manual input or field concatenation. "
        "Such records are not found by an exact value search and look "
        "untidy in reports, while a comparison with the normalized value "
        "gives a false mismatch."
    ),
    "Пробелы по краям значения проверяет отдельная "
    "проверка «Пробелы по краям значений», пустые строки — "
    "проверка «Пустые строки». В отчёте по каждому полю "
    "показывается число объектов, доля и пример значения, "
    "где пробелы заменены видимыми символами: «Москва··"
    "Сити».": (
        "Edge spaces are covered by the \"Leading and trailing spaces\" "
        "check and empty values by the \"Blank strings\" check. For every "
        "field the report shows the number of features, the share and a "
        "sample value with spaces replaced by visible symbols: "
        "\"Москва··Сити\"."
    ),
    "Значение «Москва  Сити» с двумя пробелами — "
    "отмечается 1 объект.": (
        "The value \"Москва  Сити\" with two spaces — one feature is "
        "reported."
    ),
    "Склейка полей дала «улица  Ленина   1» — отмечается "
    "как двойные пробелы внутри значения.": (
        "Field concatenation produced \"улица  Ленина   1\" — reported as "
        "double spaces inside the value."
    ),
    "Значение «Москва Сити» с одним пробелом — проблемы "
    "нет.": (
        "The value \"Москва Сити\" with a single space — no problem."
    ),
    "Слой «{}»: двойные пробелы внутри значений — "
    "затронуто полей {} из {}: {}": (
        "Layer \"{}\": double spaces inside values — {} of {} fields "
        "affected: {}"
    ),
    "Поле «{}»: двойные пробелы внутри значений у {} из {} "
    "объектов ({}%)": (
        "Field \"{}\": double spaces inside values in {} of {} features "
        "({}%)"
    ),
    "Поле «{}»: двойные пробелы внутри значений у {} из {} "
    "объектов ({}%); пример: {}": (
        "Field \"{}\": double spaces inside values in {} of {} features "
        "({}%); sample: {}"
    ),

    "Ищет значения с ведущими или замыкающими пробелами, "
    "табуляцией и переводами строк.": (
        "Looks for values with leading or trailing spaces, tabs and line "
        "breaks."
    ),
    "Для каждого векторного слоя и таблицы ZGeo читает "
    "текстовые поля и сравнивает значение с его версией "
    "без пробелов по краям. Учитываются пробел, табуляция, "
    "перевод строки, возврат каретки, вертикальная "
    "табуляция и перевод формата.": (
        "For every vector layer and table ZGeo reads the text fields and "
        "compares each value with its trimmed version. A space, tab, line "
        "feed, carriage return, vertical tab and form feed are counted."
    ),
    "Такие значения не совпадают при сравнении и "
    "соединении: «Москва» и «Москва » считаются разными. "
    "Из-за этого ломаются справочники, фильтры и связи "
    "между слоями, а группировка даёт лишние группы.": (
        "Such values do not match in comparisons and joins: \"Москва\" "
        "and \"Москва \" are considered different. This breaks "
        "dictionaries, filters and relations between layers, and grouping "
        "produces extra groups."
    ),
    "Значения, состоящие только из пробелов, эта проверка "
    "пропускает — для них есть проверка «Пустые строки». "
    "В отчёте по каждому полю показывается число объектов, "
    "доля, сколько значений с пробелами в начале и сколько "
    "в конце, и пример значения с видимыми символами "
    "пробелов: «·Москва·», «\\tТверь».": (
        "Values consisting only of spaces are skipped by this check — the "
        "\"Blank strings\" check covers them. For every field the report "
        "shows the number of features, the share, how many values have "
        "leading and trailing spaces, and a sample value with visible "
        "space symbols: \"·Москва·\", \"\\tТверь\"."
    ),
    "Значение «Москва » с пробелом в конце — отмечается "
    "1 объект.": (
        "The value \"Москва \" with a trailing space — one feature is "
        "reported."
    ),
    "Значение «  Тверь» с двумя пробелами в начале — "
    "отмечается как пробелы в начале.": (
        "The value \"  Тверь\" with two leading spaces — reported as "
        "leading spaces."
    ),
    "Значение с табуляцией в начале — отмечается «\\t» в "
    "примере.": (
        "A value with a leading tab — \"\\t\" is shown in the sample."
    ),
    "Значение «Москва» без пробелов по краям — проблемы нет.": (
        "The value \"Москва\" without leading or trailing spaces — no "
        "problem."
    ),
    "Слой «{}»: пробелы по краям значений — "
    "затронуто полей {} из {}: {}": (
        "Layer \"{}\": leading or trailing spaces — {} of {} fields "
        "affected: {}"
    ),
    "Поле «{}»: пробелы по краям у {} из {} объектов ({}%); "
    "в начале {}, в конце {}": (
        "Field \"{}\": leading or trailing spaces in {} of {} features "
        "({}%); leading {}, trailing {}"
    ),
    "Поле «{}»: пробелы по краям у {} из {} объектов ({}%); "
    "в начале {}, в конце {}; пример: {}": (
        "Field \"{}\": leading or trailing spaces in {} of {} features "
        "({}%); leading {}, trailing {}; sample: {}"
    ),

    "Ищет текстовые поля, где значение пустое или состоит "
    "только из пробелов.": (
        "Looks for text fields whose value is empty or consists only of "
        "spaces."
    ),
    "Для каждого векторного слоя и таблицы ZGeo читает "
    "текстовые поля и считает пустыми значения, которые "
    "являются пустой строкой или состоят только из "
    "пробелов, табуляции и переводов строк.": (
        "For every vector layer and table ZGeo reads the text fields and "
        "treats as blank the values that are an empty string or consist "
        "only of spaces, tabs and line breaks."
    ),
    "Для пользователя такие значения не отличаются от "
    "NULL, но ведут себя иначе в запросах: условие IS NULL "
    "их не находит, а сортировка и группировка дают "
    "отдельную группу, поэтому одна и та же «пустота» "
    "попадает в разные места отчётов.": (
        "For the user such values are indistinguishable from NULL, but "
        "they behave differently in queries: an IS NULL condition does not "
        "find them, and sorting and grouping produce a separate group, so "
        "the same \"emptiness\" lands in different places in reports."
    ),
    "В подсказке показывается сводка по слою: сколько "
    "полей затронуто и сколько пустых строк в каждом, а в "
    "отчёте — доля пустых строк по каждому полю. Проверка "
    "только сообщает о проблемах и не меняет данные.": (
        "The tooltip shows a per-layer summary: how many fields are "
        "affected and how many blank strings each one has, while the "
        "report shows the blank share per field. The check only reports "
        "problems and does not modify data."
    ),
    "Поле name: у 12 из 200 объектов пустая строка — "
    "отмечается 6% пустых строк.": (
        "The name field: 12 of 200 features have an empty string — 6% "
        "blank strings are reported."
    ),
    "Поле address: значение из трёх пробелов — считается "
    "пустой строкой.": (
        "The address field: a value of three spaces counts as a blank "
        "string."
    ),
    "Поле code: NULL у 5 объектов и пустая строка ни у "
    "одного — проблемой не считается.": (
        "The code field: NULL for 5 features and an empty string for "
        "none — not reported as a problem."
    ),
    "Слой «{}»: пустые строки вместо NULL — "
    "затронуто полей {} из {}: {}": (
        "Layer \"{}\": blank strings instead of NULL — {} of {} fields "
        "affected: {}"
    ),
    "Поле «{}»: пустые строки у {} из {} объектов ({}%)": (
        "Field \"{}\": blank strings in {} of {} features ({}%)"
    ),
    "{} — {} из {}": "{} — {} of {}",

    "Подробный список": "Detailed list",
    "Двойной щелчок открывает подробный список: {}": (
        "Double-click opens the detailed list: {}"
    ),
    "Закрыть": "Close",
    "Ищет полные дубли строк, дубли составного ключа, совпадения без "
    "учёта регистра и пробелов и частичные вхождения значений.": (
        "Looks for full row duplicates, composite key duplicates, matches "
        "ignoring case and extra spaces, and partial value occurrences."
    ),
    "Полные дубли строк: объекты, у которых совпадают все "
    "атрибутивные столбцы. Дубли составного ключа: объекты, у "
    "которых совпадают все текстовые столбцы слоя.": (
        "Full row duplicates: features where every attribute column "
        "matches. Composite key duplicates: features where every text "
        "column of the layer matches."
    ),
    "Совпадения без учёта регистра и лишних пробелов: значения "
    "приводятся к нижнему регистру, повторяющиеся пробелы сжимаются, "
    "после чего сравниваются. «Москва» и «москва » считаются дублями.": (
        "Matches ignoring case and extra spaces: values are lower-cased and "
        "repeated spaces are collapsed before comparison. \"Москва\" and "
        "\"москва \" count as duplicates."
    ),
    "Частичные вхождения: значение целиком входит в другое значение "
    "того же поля, например «ЯмалоНенецкий автономный окру» входит в "
    "«ЯмалоНенецкий автономный округ». Показывается процент вхождения "
    "— доля длины короткого значения в длинном.": (
        "Partial occurrences: a value is fully contained in another value "
        "of the same field, for example \"Yamalo-Nenets autonomous okru\" "
        "is contained in \"Yamalo-Nenets autonomous okrug\". The "
        "occurrence percent is shown — the length of the short value "
        "relative to the long one."
    ),
    "Проверка читает все объекты слоя и сравнивает значения попарно, "
    "поэтому на больших наборах данных может работать очень долго. "
    "Для защиты от зависания проверяется не более 50 000 объектов на "
    "слой, частичные вхождения — не более чем по 1000 значениям на "
    "поле, а по каждому виду дублей показывается не более 200 групп. "
    "Дубли завышают статистику, дают двойные подписи на карте и "
    "мешают объединять данные из разных источников.": (
        "The check reads every feature of a layer and compares values "
        "pairwise, so it can run very long on large datasets. To avoid "
        "hanging it inspects at most 50 000 features per layer, at most "
        "1000 values per field for partial occurrences and shows at most "
        "200 groups per duplicate kind. Duplicates inflate statistics, "
        "produce double labels on the map and prevent merging data from "
        "different sources."
    ),
    "Двойной щелчок по ячейке таблицы результатов открывает подробный "
    "список найденных дублей с процентами.": (
        "Double-clicking a results table cell opens the detailed list of "
        "found duplicates with percentages."
    ),
    "Две строки с одинаковыми значениями всех полей — отмечается "
    "полный дубль строк.": (
        "Two rows with identical values in every field — a full row "
        "duplicate is reported."
    ),
    "Поля name и code совпадают у двух объектов, остальные поля "
    "различаются — отмечается дубль составного ключа.": (
        "The name and code fields match for two features while the others "
        "differ — a composite key duplicate is reported."
    ),
    "Значения «Москва» и «москва » — отмечается совпадение без учёта "
    "регистра и пробелов.": (
        "The values \"Москва\" and \"москва \" — a match ignoring case "
        "and spaces is reported."
    ),
    "«ЯмалоНенецкий автономный окру» и «ЯмалоНенецкий автономный "
    "округ» — частичное вхождение 97.3%.": (
        "\"Yamalo-Nenets autonomous okru\" and \"Yamalo-Nenets "
        "autonomous okrug\" — a partial occurrence of 97.3%."
    ),
    "Слой «{}»: полные дубли строк — объектов {} с полностью "
    "совпадающими атрибутами (объекты: {})": (
        "Layer \"{}\": full row duplicates — {} features with completely "
        "identical attributes (features: {})"
    ),
    "Слой «{}»: дубли составного ключа по текстовым полям — "
    "объектов {} с одинаковыми значениями (объекты: {})": (
        "Layer \"{}\": composite key duplicates over text fields — {} "
        "features with identical values (features: {})"
    ),
    "Слой «{}»: поле «{}» — значения совпадают без учёта регистра и "
    "лишних пробелов: {} (объектов {} из {})": (
        "Layer \"{}\": field \"{}\" — values match ignoring case and "
        "extra spaces: {} ({} of {} features)"
    ),
    "Слой «{}»: поле «{}» — частичное вхождение: «{}» входит в «{}» "
    "({}%, объекты: {})": (
        "Layer \"{}\": field \"{}\" — partial occurrence: \"{}\" is "
        "contained in \"{}\" ({}%, features: {})"
    ),

    "Ищет табуляцию, переводы строк, возврат каретки и невидимые "
    "символы в текстовых значениях.": (
        "Looks for tabs, line breaks, carriage returns and invisible "
        "characters in text values."
    ),
    "Для каждого векторного слоя и таблицы ZGeo читает текстовые "
    "поля и ищет управляющие символы: табуляцию (TAB), перевод "
    "строки (LF), возврат каретки (CR), вертикальную табуляцию, "
    "перевод формата, NUL и ESC.": (
        "For every vector layer and table ZGeo reads the text fields and "
        "looks for control characters: tab (TAB), line feed (LF), carriage "
        "return (CR), vertical tab, form feed, NUL and ESC."
    ),
    "Невидимыми считаются неразрывный и узкий неразрывный пробелы, "
    "мягкий перенос, символы нулевой ширины, разделители строк и "
    "абзацев, метка порядка байтов и другие форматирующие символы "
    "Unicode. Обычный пробел проблемой не считается.": (
        "Invisible characters include the no-break and narrow no-break "
        "spaces, the soft hyphen, zero-width characters, line and paragraph "
        "separators, the byte order mark and other Unicode format "
        "characters. A regular space is not a problem."
    ),
    "Такие символы портят вёрстку подписей и отчётов, ломают разбор "
    "CSV и мешают сравнению строк: две визуально одинаковые подписи "
    "оказываются разными. В отчёте показываются названия символов, "
    "число объектов и пример значения, где управляющие символы "
    "заменены на \\t, \\n и \\uXXXX.": (
        "Such characters break the layout of labels and reports, corrupt "
        "CSV parsing and prevent string comparison: two visually identical "
        "labels turn out to be different. The report shows the character "
        "names, the number of features and a sample value with control "
        "characters replaced by \\t, \\n and \\uXXXX."
    ),
    "Значение «Иванов\\tИ.И.» с табуляцией — отмечается TAB (U+0009).": (
        "The value \"Ivanov\\tI.I.\" with a tab — TAB (U+0009) is reported."
    ),
    "Адрес с переводом строки внутри значения — отмечается LF (U+000A).": (
        "An address with a line break inside the value — LF (U+000A) is "
        "reported."
    ),
    "Название с неразрывным пробелом вместо обычного — отмечается "
    "NBSP (U+00A0).": (
        "A name with a no-break space instead of a regular one — "
        "NBSP (U+00A0) is reported."
    ),
    "Строка «Центральный» без управляющих символов — проблемы нет.": (
        "The string \"Central\" without control characters — no problem."
    ),
    "Слой «{}»: в поле «{}» управляющие или невидимые символы "
    "найдены у {} из {} объектов: {}": (
        "Layer \"{}\": field \"{}\" has control or invisible "
        "characters in {} of {} features: {}"
    ),
    "Слой «{}»: в поле «{}» управляющие или невидимые символы "
    "найдены у {} из {} объектов: {}; пример: «{}»": (
        "Layer \"{}\": field \"{}\" has control or invisible "
        "characters in {} of {} features: {}; example: \"{}\""
    ),

    "Результаты проверок": "Check results",
    "Сохранить таблицу результатов в файл": (
        "Save the results table to a file"
    ),
    "{}_проверки.xlsx": "{}_checks.xlsx",
    "{}_проверки.html": "{}_checks.html",
    "ZGeo — проверки": "ZGeo — checks",
    "Отметить все проверки закладки": "Select every check on this tab",
    "Снять все отметки закладки": "Clear every check on this tab",
    "Вернуть отметки проверок по умолчанию": (
        "Restore the default check selection"
    ),
    "Сначала отсканируйте папку.": "Scan a folder first.",
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
    "Проверки: уточнить размер, систему координат и количество элементов, "
    "проверить читаемость файлов, JSON и GeoJSON, имена полей, "
    "дубли имён полей, заполненность атрибутов, управляющие и невидимые "
    "символы, имена и пути файлов, набор данных, целостность "
    "GeoPackage/SQLite, метаданные и CRS, .prj, геометрии, топологию, "
    "дубли, координаты.": (
        "Checks: refine size, CRS and feature count, check file "
        "readability, validate JSON and GeoJSON, field names, field name "
        "duplicates, attribute completeness, control and invisible "
        "characters, file names and paths, dataset integrity, GeoPackage/"
        "SQLite integrity, metadata and CRS, PRJ, geometry, topology, "
        "duplicates, coordinates."
    ),
    "Выберите проверки": "Select checks",
    "Отметьте проверки, которые нужно выполнить для найденных файлов. Нажмите «i» справа, чтобы открыть подробное описание с примерами.": (
        "Select the checks to run on the found files. Click “i” on the "
        "right to open a detailed description with examples."
    ),
    "Уточнить размер": "Refine size",
    "Считает полный размер каждого набора данных с учётом сопутствующих файлов.": (
        "Calculates the full size of each dataset, including sidecar files."
    ),
    "Проверка читаемости файлов": "File readability check",
    "Открывает каждый файл через провайдеры QGIS и проверяет, что слои и данные читаются.": (
        "Opens every file through QGIS providers and checks that layers "
        "and data can be read."
    ),
    "ZGeo открывает каждый файл через провайдеры QGIS, проверяет наличие доступных слоёв и читает один объект векторного слоя или небольшую выборку пикселей растра.": (
        "ZGeo opens every file through QGIS providers, checks that layers "
        "are available and reads one feature from each vector layer or a "
        "small sample of raster pixels."
    ),
    "Для векторных слоёв читаются атрибуты и геометрия первого объекта; для растров — несколько пикселей по всей области данных. Полный файл не читается, поэтому проверка остаётся быстрой.": (
        "For vector layers, the attributes and geometry of the first "
        "feature are read; for rasters, several pixels across the data "
        "extent are read. The full file is not read, so the check stays "
        "fast."
    ),
    "Проверка отмечает отсутствующие и пустые файлы, файлы без доступных слоёв, ошибки открытия и ошибки чтения данных. Пустые слои и проблемы геометрии проверяются отдельными проверками.": (
        "The check flags missing and empty files, files without available "
        "layers, open errors and data read errors. Empty layers and "
        "geometry problems are covered by separate checks."
    ),
    "Повреждённый GeoTIFF не открывается провайдером GDAL — файл отмечается.": (
        "A corrupted GeoTIFF cannot be opened by the GDAL provider — the "
        "file is flagged."
    ),
    "В GeoPackage один слой читается, а данные другого повреждены — отмечается ошибка чтения слоя.": (
        "In a GeoPackage, one layer is readable while another is "
        "corrupted — a layer read error is flagged."
    ),
    "Файл размером 0 байт — отмечается как пустой.": (
        "A file of 0 bytes is flagged as empty."
    ),
    "Файл не найден или недоступен": (
        "The file is missing or inaccessible"
    ),
    "Файл пуст (0 байт)": "The file is empty (0 bytes)",
    "QGIS не смог открыть файл: нет доступных слоёв": (
        "QGIS could not open the file: no layers are available"
    ),
    "QGIS не смог открыть файл{}": "QGIS could not open the file{}",
    "Не удалось прочитать объект из слоя «{}»{}": (
        "Could not read a feature from layer “{}”{}"
    ),
    "Не удалось прочитать данные растра «{}»{}": (
        "Could not read raster data from layer “{}”{}"
    ),
    "Проверка целостности GeoPackage/SQLite": (
        "GeoPackage/SQLite integrity check"
    ),
    "Проверяет целостность базы SQLite, внешние ключи и структуру GeoPackage.": (
        "Checks SQLite integrity, foreign keys and GeoPackage structure."
    ),
    "Для файлов .gpkg, .sqlite и .spatialite ZGeo открывает базу только для чтения и выполняет PRAGMA quick_check; при обнаружении ошибок дополнительно запускается PRAGMA integrity_check.": (
        "For .gpkg, .sqlite and .spatialite files, ZGeo opens the database "
        "read-only and runs PRAGMA quick_check; if errors are found, "
        "PRAGMA integrity_check is run as well."
    ),
    "Затем выполняется PRAGMA foreign_key_check. Для GeoPackage проверяются обязательные таблицы gpkg_contents, gpkg_geometry_columns и gpkg_spatial_ref_sys, наличие таблиц и геометрических колонок, ссылки на SRS и совпадение srs_id между gpkg_contents и gpkg_geometry_columns.": (
        "Then PRAGMA foreign_key_check is run. For GeoPackage, the "
        "required gpkg_contents, gpkg_geometry_columns and "
        "gpkg_spatial_ref_sys tables are checked, along with table and "
        "geometry column existence, SRS references and srs_id consistency "
        "between gpkg_contents and gpkg_geometry_columns."
    ),
    "Проверка не изменяет файл. Для обычных SQLite-баз без таблиц GeoPackage проверяются только целостность и внешние ключи.": (
        "The check does not modify the file. For ordinary SQLite "
        "databases without GeoPackage tables, only integrity and foreign "
        "keys are checked."
    ),
    "Повреждённый блок SQLite обнаруживается PRAGMA quick_check.": (
        "A corrupted SQLite block is detected by PRAGMA quick_check."
    ),
    "В gpkg_geometry_columns указан srs_id, которого нет в gpkg_spatial_ref_sys.": (
        "gpkg_geometry_columns contains an srs_id that is missing from "
        "gpkg_spatial_ref_sys."
    ),
    "В gpkg_contents есть векторная таблица, но для неё нет записи в gpkg_geometry_columns.": (
        "gpkg_contents contains a feature table but gpkg_geometry_columns "
        "has no entry for it."
    ),
    "Не удалось открыть SQLite: {}": "Could not open SQLite: {}",
    "Проверка целостности SQLite: {}": "SQLite integrity check: {}",
    "Нарушений целостности SQLite: {} (показаны первые {})": (
        "SQLite integrity violations: {} (first {} shown)"
    ),
    "Не удалось проверить внешние ключи: {}": (
        "Could not check foreign keys: {}"
    ),
    "Нарушение внешнего ключа: таблица {}, строка {}, родительская таблица {}": (
        "Foreign key violation: table {}, row {}, parent table {}"
    ),
    "Нарушений внешнего ключа: {} (показаны первые {})": (
        "Foreign key violations: {} (first {} shown)"
    ),
    "В GeoPackage отсутствует обязательная таблица: {}": (
        "GeoPackage is missing a required table: {}"
    ),
    "Не удалось прочитать таблицы GeoPackage: {}": (
        "Could not read GeoPackage tables: {}"
    ),
    "Некорректная запись gpkg_geometry_columns: пустое имя таблицы или колонки": (
        "Invalid gpkg_geometry_columns row: empty table or column name"
    ),
    "Геометрическая колонка {}: таблица {} отсутствует в gpkg_contents": (
        "Geometry column {}: table {} is missing from gpkg_contents"
    ),
    "Таблица {} в gpkg_contents имеет тип {}, ожидается features": (
        "Table {} in gpkg_contents has type {}, expected features"
    ),
    "Геометрическая колонка {}: не указан srs_id": (
        "Geometry column {}: srs_id is not set"
    ),
    "Геометрическая колонка {}: srs_id {} отсутствует в gpkg_spatial_ref_sys": (
        "Geometry column {}: srs_id {} is missing from "
        "gpkg_spatial_ref_sys"
    ),
    "Несовпадение srs_id для таблицы {}: gpkg_contents={}, gpkg_geometry_columns={}": (
        "srs_id mismatch for table {}: gpkg_contents={}, "
        "gpkg_geometry_columns={}"
    ),
    "Геометрическая колонка {}: в таблице {} нет такой колонки": (
        "Geometry column {}: table {} has no such column"
    ),
    "Таблица {} из gpkg_contents отсутствует в базе": (
        "Table {} from gpkg_contents is missing from the database"
    ),
    "Для таблицы {} нет записи в gpkg_geometry_columns": (
        "No gpkg_geometry_columns entry for table {}"
    ),
    "В gpkg_contents для таблицы {} не указан srs_id": (
        "srs_id is not set in gpkg_contents for table {}"
    ),
    "неизвестная ошибка": "unknown error",
    "Уточнить систему координат": "Refine CRS",
    "Читает систему координат слоёв и обновляет колонку «Система координат».": (
        "Reads the CRS of layers and updates the “CRS” column."
    ),
    "Уточнить количество элементов": "Refine feature count",
    "Считает количество элементов слоёв и обновляет колонку «Элементов».": (
        "Counts layer features and updates the “Features” column."
    ),
    "Считает количество элементов и обновляет колонку «Элементов».": (
        "Counts features and updates the “Features” column."
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
    "Проверка GeoJSON": "GeoJSON check",
    "Проверяет координаты, замкнутость колец, bbox и структуру Feature/GeometryCollection в файлах GeoJSON.": (
        "Checks coordinates, ring closure, bbox and Feature/"
        "GeometryCollection structure in GeoJSON files."
    ),
    "Для каждого файла .json и .geojson ZGeo разбирает документ и проверяет координаты: числовой тип, отсутствие NaN/Inf, диапазон долготы и широты, признаки перепутанных широты и долготы.": (
        "For each .json and .geojson file ZGeo parses the document and "
        "checks coordinates: numeric type, absence of NaN/Inf, longitude "
        "and latitude range, and signs of swapped latitude and longitude."
    ),
    "Проверяются позиции, линии и кольца: минимальное число точек, замкнутость первого и последнего положения кольца и соответствие вложенности типу геометрии.": (
        "Positions, lines and rings are checked: the minimum number of "
        "points, whether the first and last ring positions match, and "
        "whether the nesting matches the geometry type."
    ),
    "Необязательный bbox проверяется на уровне документа, объекта, геометрии и коллекции: длина 4 или 6 чисел, конечные значения и порядок минимума и максимума. Также проверяются обязательные поля и структура Feature, FeatureCollection и GeometryCollection.": (
        "The optional bbox is validated at document, feature, geometry "
        "and collection level: a length of 4 or 6 numbers, finite values "
        "and minimum/maximum order. Required fields and the structure of "
        "Feature, FeatureCollection and GeometryCollection are also "
        "checked."
    ),
    "FeatureCollection с корректными координатами и замкнутыми кольцами — проблем не найдено.": (
        "A FeatureCollection with valid coordinates and closed rings — no "
        "issues found."
    ),
    "Полигон, у которого первая и последняя точки кольца не совпадают — отмечается «Кольцо не замкнуто».": (
        "A polygon whose first and last ring positions do not match — "
        "“Ring is not closed” is flagged."
    ),
    "bbox [0, 0, 10] — отмечается неверное число значений; координата [200, 95] — перепутанные широта и долгота.": (
        "bbox [0, 0, 10] — an invalid number of values is flagged; the "
        "coordinate [200, 95] — swapped latitude and longitude."
    ),
    "Ошибок GeoJSON: {} (координаты: {}, кольца: {}, bbox: {}, структура: {})": (
        "GeoJSON issues: {} (coordinates: {}, rings: {}, bbox: {}, "
        "structure: {})"
    ),
    "Дополнительные ошибки не показаны (лимит {}).": (
        "Additional issues are not shown (limit {})."
    ),
    "Не удалось прочитать GeoJSON: {}": "Could not read GeoJSON: {}",
    "Не удалось проверить GeoJSON: {}": "Could not validate GeoJSON: {}",
    "Корень GeoJSON должен быть объектом": (
        "The GeoJSON root must be an object"
    ),
    "Отсутствует или неверен тип GeoJSON: {}": (
        "The GeoJSON type is missing or invalid: {}"
    ),
    "Неизвестный тип GeoJSON: {}": "Unknown GeoJSON type: {}",
    "Отсутствует обязательное поле «features»": (
        "The required “features” field is missing"
    ),
    "Поле «features» должно быть массивом": (
        "The “features” field must be an array"
    ),
    "Элемент FeatureCollection должен быть объектом Feature": (
        "A FeatureCollection element must be a Feature object"
    ),
    "Тип объекта Feature должен быть «Feature»: {}": (
        "A Feature object type must be “Feature”: {}"
    ),
    "Отсутствует обязательное поле «geometry»": (
        "The required “geometry” field is missing"
    ),
    "Поле «geometry» должно быть объектом или null": (
        "The “geometry” field must be an object or null"
    ),
    "Отсутствует обязательное поле «properties»": (
        "The required “properties” field is missing"
    ),
    "Поле «properties» должно быть объектом или null": (
        "The “properties” field must be an object or null"
    ),
    "Поле «id» должно быть строкой или числом": (
        "The “id” field must be a string or a number"
    ),
    "Отсутствует обязательное поле «geometries»": (
        "The required “geometries” field is missing"
    ),
    "Поле «geometries» должно быть массивом": (
        "The “geometries” field must be an array"
    ),
    "Элемент GeometryCollection должен быть объектом геометрии": (
        "A GeometryCollection element must be a geometry object"
    ),
    "Тип GeometryCollection должен быть «GeometryCollection»: {}": (
        "A GeometryCollection type must be “GeometryCollection”: {}"
    ),
    "Отсутствует или неверен тип геометрии: {}": (
        "The geometry type is missing or invalid: {}"
    ),
    "Неизвестный тип геометрии: {}": "Unknown geometry type: {}",
    "Отсутствует обязательное поле «coordinates»": (
        "The required “coordinates” field is missing"
    ),
    "Поле «coordinates» должно быть массивом": (
        "The “coordinates” field must be an array"
    ),
    "Поле «bbox» должно быть массивом чисел": (
        "The “bbox” field must be an array of numbers"
    ),
    "Поле «bbox» должно содержать 4 или 6 чисел": (
        "The “bbox” field must contain 4 or 6 numbers"
    ),
    "Элемент bbox должен быть числом: {}": (
        "A bbox element must be a number: {}"
    ),
    "Элемент bbox не должен быть NaN/Inf": (
        "A bbox element must not be NaN/Inf"
    ),
    "bbox: минимум больше максимума по оси {}": (
        "bbox: minimum is greater than maximum on axis {}"
    ),
    "Позиция должна быть массивом чисел": (
        "A position must be an array of numbers"
    ),
    "Позиция должна содержать не менее двух чисел": (
        "A position must contain at least two numbers"
    ),
    "Координата должна быть числом: {}": (
        "A coordinate must be a number: {}"
    ),
    "Долгота вне диапазона [-180, 180]: {}": (
        "Longitude is outside the [-180, 180] range: {}"
    ),
    "Широта вне диапазона [-90, 90]: {}": (
        "Latitude is outside the [-90, 90] range: {}"
    ),
    "LineString должен быть массивом позиций": (
        "A LineString must be an array of positions"
    ),
    "LineString должен содержать не менее {} точек": (
        "A LineString must contain at least {} points"
    ),
    "LineString должен содержать не менее 2 точек": (
        "A LineString must contain at least 2 points"
    ),
    "Кольцо должно быть массивом позиций": (
        "A ring must be an array of positions"
    ),
    "Кольцо должно содержать не менее 4 точек": (
        "A ring must contain at least 4 points"
    ),
    "Кольцо не замкнуто: первая и последняя точки не совпадают": (
        "The ring is not closed: the first and last positions differ"
    ),
    "Полигон должен содержать хотя бы одно кольцо": (
        "A polygon must contain at least one ring"
    ),
    "Полигон в MultiPolygon должен быть массивом колец": (
        "A MultiPolygon polygon must be an array of rings"
    ),
    "Структура GeoJSON слишком глубокая": (
        "The GeoJSON structure is too deeply nested"
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
    "Проверка дублей имён полей": "Field name duplicates check",
    "Ищет имена атрибутивных полей, совпадающие без учёта регистра в одном слое.": (
        "Finds attribute field names that match ignoring case within the "
        "same layer."
    ),
    "Для каждого векторного слоя ZGeo сравнивает имена полей после приведения к нижнему регистру. Поля Name и name считаются дублями.": (
        "For each vector layer, ZGeo compares field names case-insensitively. "
        "Fields Name and name are treated as duplicates."
    ),
    "Сравнение выполняется только внутри одного слоя; одинаковые имена в разных слоях не считаются дублями.": (
        "The comparison is limited to a single layer; identical names in "
        "different layers are not treated as duplicates."
    ),
    "Поля Name и name в одном слое — отмечается дубль.": (
        "Fields Name and name in one layer — duplicate is flagged."
    ),
    "Поля CODE и code в одном слое — отмечается дубль.": (
        "Fields CODE and code in one layer — duplicate is flagged."
    ),
    "Поле name в двух разных слоях — дублем не считается.": (
        "A name field in two different layers is not treated as a duplicate."
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
    "Проверка .prj-файла": "PRJ file check",
    "Проверяет наличие файла .prj, его читаемость и согласованность с системой координат слоя.": (
        "Checks that the .prj file exists, is readable and matches the "
        "CRS of the layer."
    ),
    "ZGeo ищет файл .prj рядом с набором данных и разбирает его содержимое как WKT: проверяются наличие, кодировка, пустой файл, парность скобок и корневой тип системы координат.": (
        "ZGeo looks for the .prj file next to the dataset and parses its "
        "content as WKT: presence, encoding, an empty file, balanced "
        "brackets and the root CRS type are checked."
    ),
    "Затем сведения из .prj сравниваются с системой координат слоя: тип (географическая или проекционная) и код EPSG, если он указан в .prj.": (
        "The .prj content is then compared with the CRS of the layer: the "
        "type (geographic or projected) and the EPSG code, when the .prj "
        "contains one."
    ),
    "Если файла .prj нет, но есть .qpj, замечание не выводится: QGIS использует .qpj как замену.": (
        "If the .prj file is missing but a .qpj file is present, no issue "
        "is reported: QGIS uses .qpj as a replacement."
    ),
    "roads.prj с WKT EPSG:3857 и слой в EPSG:3857 — проблема не найдена.": (
        "roads.prj with WKT EPSG:3857 and a layer in EPSG:3857 — no issue "
        "is found."
    ),
    "Пустой roads.prj — отмечается «Файл .prj пуст».": (
        "An empty roads.prj — “The .prj file is empty” is flagged."
    ),
    "В .prj географическая система, а слой в проекционной — отмечается несовпадение типа CRS.": (
        "The .prj holds a geographic CRS while the layer is projected — a "
        "CRS type mismatch is flagged."
    ),
    "Нет файла .prj: система координат слоя не закреплена": (
        "No .prj file: the layer CRS is not fixed in a file"
    ),
    "Не удалось прочитать файл .prj: {}": "Could not read the .prj file: {}",
    "Файл .prj пуст: система координат не указана": (
        "The .prj file is empty: no CRS is specified"
    ),
    "Файл .prj не содержит корректного WKT: {}": (
        "The .prj file does not contain valid WKT: {}"
    ),
    "Тип системы координат в .prj не совпадает с CRS слоя: в .prj {}, у слоя {}": (
        "The CRS type in the .prj does not match the layer CRS: the .prj "
        "is {}, the layer is {}"
    ),
    "Файл .prj не соответствует CRS слоя: в .prj EPSG:{}, у слоя {}": (
        "The .prj file does not match the layer CRS: the .prj is EPSG:{}, "
        "the layer is {}"
    ),
    "географическая": "geographic",
    "проекционная": "projected",
    "иная": "other",
    "Проверка валидности геометрий": "Geometry validity check",
    "Ищет самопересечения, незамкнутые кольца, пустые и null-геометрии.": (
        "Finds self-intersections, unclosed rings, empty and null geometries."
    ),
    "Проверка топологии": "Topology check",
    "Ищет наложения и разрывы полигонов, висячие линии и пересечения линий.": (
        "Finds polygon overlaps and gaps, dangling lines and line "
        "intersections."
    ),
    "Для полигонов ZGeo проверяет попарные наложения по площади и ищет замкнутые разрывы внутри объединения слоя. Разрыв учитывается, если его граница соприкасается с двумя или более объектами; внутренние отверстия одного полигона не считаются разрывом.": (
        "For polygons, ZGeo checks pairwise overlaps by area and looks for "
        "enclosed gaps inside the layer union. A gap is reported if its "
        "boundary touches two or more features; interior holes of a single "
        "polygon are not considered gaps."
    ),
    "Для линий проверяются свободные концы: конец считается висячим, если он не совпадает с концом другой линии и не лежит на другой линии. Пересечения внутри линий и наложения линий отмечаются отдельно; соединения в конечных точках, включая T-образные, не считаются пересечением.": (
        "For lines, free endpoints are checked: an endpoint is dangling if "
        "it does not coincide with another line endpoint and does not lie "
        "on another line. Interior crossings and line overlaps are "
        "reported separately; connections at endpoints, including "
        "T-junctions, are not considered intersections."
    ),
    "Некорректные и пустые геометрии пропускаются — для них есть отдельная проверка валидности. Подробно описывается до 1000 замечаний на слой.": (
        "Invalid and empty geometries are skipped; a separate validity "
        "check covers them. Up to 1,000 issues per layer are described in "
        "detail."
    ),
    "Два полигона перекрываются на площади 12.5 — отмечается наложение.": (
        "Two polygons overlap over an area of 12.5 — an overlap is reported."
    ),
    "Полигоны образуют кольцо с незаполненной областью — отмечается разрыв.": (
        "Polygons form a ring with an unfilled area — a gap is reported."
    ),
    "Линия заканчивается в пустоте — отмечается висячая линия.": (
        "A line ends in empty space — a dangling line is reported."
    ),
    "Две линии пересекаются в точке, не являющейся концом ни одной из них — отмечается пересечение.": (
        "Two lines intersect at a point that is not an endpoint of either "
        "line — an intersection is reported."
    ),
    "Две линии частично идут по одному и тому же участку — отмечается наложение линий.": (
        "Two lines partially follow the same segment — a line overlap is "
        "reported."
    ),
    "Проверка дублей объектов": "Duplicate features check",
    "Ищет объекты с полностью совпадающей геометрией.": (
        "Finds features with completely identical geometry."
    ),
    "Для каждого векторного слоя ZGeo сравнивает геометрию объектов побайтово: в ключ входит тип геометрии, число вершин и все координаты, включая Z.": (
        "For each vector layer ZGeo compares feature geometries byte by "
        "byte: the key includes the geometry type, the vertex count and "
        "all coordinates, including Z."
    ),
    "Пустые и null-геометрии не сравниваются. Для групп совпадений показывается первый объект и номера его дублей; подробно описывается до 1000 дублей на слой.": (
        "Empty and null geometries are not compared. For each group of "
        "matches the first feature and the numbers of its duplicates are "
        "shown; up to 1,000 duplicates per layer are described in detail."
    ),
    "Объекты с одинаковыми координатами, но разными атрибутами тоже считаются дублями геометрии: ZGeo сравнивает только геометрию.": (
        "Features with identical coordinates but different attributes are "
        "also treated as geometry duplicates: ZGeo compares the geometry "
        "only."
    ),
    "Два полигона с одинаковым набором вершин — второй отмечается как «Дубль геометрии объекта 1».": (
        "Two polygons with the same vertex set — the second is flagged as "
        "“Duplicate geometry of feature 1”."
    ),
    "Объекты с одинаковым контуром, но разными атрибутами — тоже дубль геометрии.": (
        "Features with the same outline but different attributes are also "
        "geometry duplicates."
    ),
    "Объекты с совпадающими координатами, но разным порядком вершин — не дубли.": (
        "Features with matching coordinates but a different vertex order "
        "are not duplicates."
    ),
    "Дубль геометрии объекта {} — совпадает с объектом {}": (
        "Duplicate geometry of feature {} — matches feature {}"
    ),
    "Слой «{}»: дублей по геометрии: {}, групп: {}": (
        "Layer “{}”: geometry duplicates: {}, groups: {}"
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
    "Подробное описание": "Detailed description",
    "Подробное описание проверки": "Detailed check description",
    "Закрыть описание": "Close description",
    "Что будет сделано": "What will be done",
    "Примеры": "Examples",
    "Для каждого файла ZGeo складывает размер основного файла и всех связанных файлов набора в той же папке. Значения берутся из файловой системы и заменяют приблизительный размер, показанный после сканирования.": (
        "For each file, ZGeo adds the size of the main file and all related "
        "dataset files in the same folder. The values come from the file "
        "system and replace the approximate size shown after scanning."
    ),
    "В колонке «Размер» и в отчётах показывается полный объём набора. Если связанный файл отсутствует, учитываются только существующие файлы.": (
        "The “Size” column and reports show the full dataset size. If a "
        "related file is missing, only the existing files are counted."
    ),
    "roads.shp + roads.shx + roads.dbf + roads.prj + roads.cpg — полный размер Shapefile.": (
        "roads.shp + roads.shx + roads.dbf + roads.prj + roads.cpg — full "
        "Shapefile size."
    ),
    "roads.mif + roads.mid — полный размер MapInfo MIF/MID.": (
        "roads.mif + roads.mid — full MapInfo MIF/MID size."
    ),
    "dem.tif + dem.tif.aux.xml + dem.tif.ovr + dem.tfw — полный размер растрового набора.": (
        "dem.tif + dem.tif.aux.xml + dem.tif.ovr + dem.tfw — full raster "
        "dataset size."
    ),
    "ZGeo открывает каждый слой через провайдеры QGIS, читает его систему координат и записывает название в колонку «Система координат».": (
        "ZGeo opens each layer through QGIS providers, reads its coordinate "
        "system and writes the name to the “CRS” column."
    ),
    "Проверка отмечает файлы, у которых система координат не определена или неизвестна, а также файлы, в которых слои используют разные системы координат.": (
        "The check flags files with an undefined or unknown coordinate "
        "system, as well as files whose layers use different coordinate "
        "systems."
    ),
    "Для растров система координат читается из метаданных растра; если её нет, значение остаётся неопределённым.": (
        "For rasters, the coordinate system is read from the raster "
        "metadata; if it is missing, the value remains undefined."
    ),
    "EPSG:3857 — WGS 84 / Pseudo-Mercator: проблема не найдена.": (
        "EPSG:3857 — WGS 84 / Pseudo-Mercator: no problem found."
    ),
    "Пустое значение или «Не определена»: файл помечается как проблемный.": (
        "An empty value or “Undefined”: the file is flagged as a problem."
    ),
    "Два слоя GeoPackage с EPSG:3857 и EPSG:4326: отмечается смешанная система координат.": (
        "Two GeoPackage layers with EPSG:3857 and EPSG:4326: mixed "
        "coordinate system is flagged."
    ),
    "Для каждого слоя ZGeo считает объекты через провайдеры QGIS и обновляет колонку «Элементов».": (
        "For each layer, ZGeo counts features through QGIS providers and "
        "updates the “Features” column."
    ),
    "Пустой слой отмечается отдельно. Если в файле нет ни одного объекта, файл помечается как не содержащий объектов.": (
        "An empty layer is flagged separately. If a file has no features at "
        "all, the file is flagged as containing no features."
    ),
    "Для растров количество элементов не подсчитывается.": (
        "Feature counts are not calculated for rasters."
    ),
    "Для каждого слоя ZGeo считает объекты через провайдеры QGIS и обновляет колонку «Элементов». Для файлов с несколькими слоями количество суммируется.": (
        "For each layer ZGeo counts the features through QGIS providers and "
        "updates the “Features” column. For files with several layers the "
        "counts are summed."
    ),
    "Проверка только заполняет колонку и не отмечает файлы как проблемные: пустые слои и файлы без объектов ищут проверки атрибутивных данных.": (
        "The check only fills the column and does not flag files as "
        "problematic: empty layers and files without features are found by "
        "the attribute data checks."
    ),
    "Для растров количество элементов не подсчитывается, в колонке остаётся «—».": (
        "Raster feature counts are not calculated, the column keeps “—”."
    ),
    "Слой roads: 1 245 объектов — колонка обновлена.": (
        "Layer roads: 1 245 features — the column is updated."
    ),
    "GeoPackage из двух слоёв: 1 245 и 380 объектов — в колонке 1 625.": (
        "A GeoPackage with two layers: 1 245 and 380 features — the column "
        "shows 1 625."
    ),
    "Слой buildings: 0 объектов — колонка показывает 0, проблема не отмечается.": (
        "Layer buildings: 0 features — the column shows 0, no problem is "
        "reported."
    ),
    "Слой roads: 1 245 объектов — проблема не найдена.": (
        "roads layer: 1,245 features — no problem found."
    ),
    "Слой buildings: 0 объектов — отмечается пустой слой.": (
        "buildings layer: 0 features — empty layer is flagged."
    ),
    "GeoPackage из двух пустых слоёв: файл помечается как не содержащий объектов.": (
        "A GeoPackage with two empty layers: the file is flagged as "
        "containing no features."
    ),
    "Для векторных слоёв ZGeo читает имена атрибутивных полей и проверяет нелатинские символы, длину больше 10 символов (ограничение DBF), пробелы и символы, кроме букв, цифр и подчёркивания.": (
        "For vector layers, ZGeo reads attribute field names and checks for "
        "non-Latin characters, names longer than 10 characters (the DBF "
        "limit), spaces, and characters other than letters, digits and "
        "underscores."
    ),
    "Отдельно ищутся имена, которые совпадают после усечения до 10 символов.": (
        "Names that collide after truncation to 10 characters are also "
        "checked."
    ),
    "Для растров проверка не применяется.": (
        "The check does not apply to rasters."
    ),
    "Поле «Наименование»: нелатинские символы — отмечается.": (
        "Field “Наименование” (Name): non-Latin characters — flagged."
    ),
    "Поле very_long_field_name: длина больше 10 символов — отмечается.": (
        "Field very_long_field_name: longer than 10 characters — flagged."
    ),
    "Поля population_2024 и population_2025: после усечения до 10 символов совпадают — отмечается дубль.": (
        "Fields population_2024 and population_2025: they collide after "
        "truncation to 10 characters — duplicate is flagged."
    ),
    "ZGeo проверяет обязательные файлы набора: для SHP — .dbf и .shx, для MIF — .mid, для TAB — .dat, .map и .id.": (
        "ZGeo checks the required dataset files: .dbf and .shx for SHP, "
        ".mid for MIF, and .dat, .map and .id for TAB."
    ),
    "Для SHP дополнительно проверяется наличие .cpg и корректность указанной в нём кодировки DBF.": (
        "For SHP, the presence of .cpg and the validity of the DBF encoding "
        "specified in it are also checked."
    ),
    "Проверка не меняет список файлов и ищет сопутствующие файлы в той же папке.": (
        "The check does not change the file list and looks for related "
        "files in the same folder."
    ),
    "roads.shp без roads.dbf и roads.shx — отмечается отсутствие файлов набора.": (
        "roads.shp without roads.dbf and roads.shx — missing dataset files "
        "are flagged."
    ),
    "roads.shp + roads.dbf + roads.shx без roads.cpg — отмечается отсутствие .cpg.": (
        "roads.shp + roads.dbf + roads.shx without roads.cpg — missing "
        ".cpg is flagged."
    ),
    "roads.cpg с текстом UTF-8 — кодировка распознана; с текстом x-unknown — отмечается неизвестная кодировка.": (
        "roads.cpg containing UTF-8 — encoding recognized; containing "
        "x-unknown — unknown encoding is flagged."
    ),
    "Для SHP проверяется наличие .prj (или .qpj) и .cpg. Для растров проверяется наличие .aux.xml и .ovr, а если система координат не определена — файла привязки .tfw, .tifw или .wld.": (
        "For SHP, the presence of .prj (or .qpj) and .cpg is checked. For "
        "rasters, the presence of .aux.xml and .ovr is checked, and if the "
        "coordinate system is undefined, a .tfw, .tifw or .wld world file "
        "is checked."
    ),
    "Для слоёв проверяются устаревшие системы координат, отсутствие кода EPSG или другого авторитета, неметрические единицы у проекционных систем, не градусы у географических систем и нестандартный порядок осей YX.": (
        "Layers are checked for deprecated coordinate systems, missing "
        "EPSG or other authority codes, non-metric units in projected "
        "systems, non-degree units in geographic systems, and non-standard "
        "YX axis order."
    ),
    "roads.shp без roads.prj — отмечается отсутствие метаданных системы координат.": (
        "roads.shp without roads.prj — missing coordinate system metadata "
        "is flagged."
    ),
    "dem.tif без dem.tif.aux.xml и dem.tif.ovr — отмечаются отсутствующие вспомогательные метаданные.": (
        "dem.tif without dem.tif.aux.xml and dem.tif.ovr — missing "
        "auxiliary metadata is flagged."
    ),
    "Слой в EPSG:3857 с единицами «футы» — отмечаются неметрические единицы.": (
        "A layer in EPSG:3857 with “feet” units — non-metric units are "
        "flagged."
    ),
    "Для каждого векторного слоя ZGeo перебирает объекты и проверяет геометрию: null и пустые геометрии, незамкнутые кольца, самопересечения и прочие ошибки валидности.": (
        "For each vector layer, ZGeo iterates over features and checks the "
        "geometry: null and empty geometries, unclosed rings, "
        "self-intersections and other validity errors."
    ),
    "Итоги группируются по слою, а для найденных ошибок сохраняются номер объекта и вершины; подробно описывается до 1000 ошибок на слой.": (
        "Results are grouped by layer, and the feature and vertex numbers "
        "are saved for the found errors; up to 1,000 errors per layer are "
        "described in detail."
    ),
    "Полигон с самопересечением — отмечается «Самопересечение».": (
        "A polygon with a self-intersection — “Self-intersection” is "
        "flagged."
    ),
    "Координата (500, 95) в географической системе — отмечается «Похоже на перепутанные широту и долготу».": (
        "Coordinate (500, 95) in a geographic system — “Possibly swapped "
        "latitude and longitude” is flagged."
    ),
    "Вершина с координатой NaN — отмечается «Координата NaN/Inf».": (
        "A vertex with a NaN coordinate — “NaN/Inf coordinate” is flagged."
    ),
    "ZGeo читает каждый файл .json и .geojson и проверяет структуру по полю type: допустимые типы геометрий, Feature, FeatureCollection и GeometryCollection, а также обязательные вложенные поля features и geometries.": (
        "ZGeo reads every .json and .geojson file and validates the "
        "structure by the type field: valid geometry types, Feature, "
        "FeatureCollection and GeometryCollection, as well as the required "
        "nested features and geometries fields."
    ),
    "Содержимое координат не анализируется. Файлы, которые не читаются как JSON или не являются GeoJSON, исключаются из списка и не участвуют в остальных проверках.": (
        "Coordinate contents are not analyzed. Files that cannot be read "
        "as JSON or are not GeoJSON are excluded from the list and do not "
        "participate in other checks."
    ),
    '{"type": "FeatureCollection", "features": [...]} — GeoJSON, файл остаётся в списке.': (
        '{"type": "FeatureCollection", "features": [...]} — GeoJSON, the '
        "file remains in the list."
    ),
    '{"type": "Feature", "geometry": {...}, "properties": {...}} — GeoJSON, файл остаётся.': (
        '{"type": "Feature", "geometry": {...}, "properties": {...}} — '
        "GeoJSON, the file remains."
    ),
    '{"name": "settings", "values": [...]} — не GeoJSON, файл исключается.': (
        '{"name": "settings", "values": [...]} — not GeoJSON, the file is '
        "excluded."
    ),
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
    "В наборе отсутствует файл метаданных: {}": (
        "Dataset is missing a metadata file: {}"
    ),
    "Нет вспомогательных метаданных: {}": (
        "No auxiliary metadata: {}"
    ),
    "Нет файла привязки .tfw/.tifw/.wld: растровая привязка не найдена": (
        "No .tfw/.tifw/.wld world file: raster georeferencing not found"
    ),
    "Слой «{}»: система координат не определена": (
        "Layer “{}”: coordinate system is not defined"
    ),
    "Слой «{}»: устаревшая система координат {} — {}": (
        "Layer “{}”: deprecated coordinate system {} — {}"
    ),
    "Слой «{}»: система координат без кода EPSG/авторитета": (
        "Layer “{}”: coordinate system has no EPSG/authority code"
    ),
    "Слой «{}»: не метрические единицы CRS: {}": (
        "Layer “{}”: non-metric CRS units: {}"
    ),
    "Слой «{}»: для географической CRS ожидаются градусы, указано: {}": (
        "Layer “{}”: geographic CRS expects degrees, got: {}"
    ),
    "Слой «{}»: нестандартный порядок осей CRS (YX)": (
        "Layer “{}”: non-standard CRS axis order (YX)"
    ),
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
    "Слой «{}»: имена полей совпадают без учёта регистра: {}": (
        "Layer “{}”: field names match ignoring case: {}"
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
    "Проверка имён и путей файлов": "File name and path check",
    "Проверяет длину пути, недопустимые символы и зарезервированные имена, совпадения имён без учёта регистра и осиротевшие сопутствующие файлы.": (
        "Checks the path length, invalid characters and reserved names, "
        "case-insensitive name collisions and orphaned sidecar files."
    ),
    "Для каждого найденного файла проверяются длина полного пути (больше 260 символов — ограничение Windows), символы <>:\"|?* и управляющие символы в имени, зарезервированные имена (CON, PRN, AUX, NUL, COM1-9, LPT1-9) и завершение имени пробелом или точкой.": (
        "Every found file is checked for the full path length (more than "
        "260 characters is a Windows limit), the characters <>:\"|?* and "
        "control characters in the name, reserved names (CON, PRN, AUX, "
        "NUL, COM1-9, LPT1-9) and a name that ends with a space or a dot."
    ),
    "В каждой папке ZGeo ищет файлы, имена которых различаются только регистром, а также осиротевшие сопутствующие файлы: roads.dbf, roads.prj, dem.tif.aux.xml и подобные без основного файла набора.": (
        "In every folder ZGeo looks for files whose names differ only by "
        "case, and for orphaned sidecar files: roads.dbf, roads.prj, "
        "dem.tif.aux.xml and similar without a main dataset file."
    ),
    "Проверка только сообщает о проблемах и не переименовывает файлы. Результаты по папке показываются один раз — у первого файла папки.": (
        "The check only reports problems and never renames files. Folder "
        "results are shown once, on the first file of the folder."
    ),
    "Путь в 275 символов — отмечается превышение ограничения Windows.": (
        "A path of 275 characters — exceeding the Windows limit is "
        "flagged."
    ),
    "В папке есть roads.dbf без roads.shp — отмечается осиротевший сопутствующий файл.": (
        "The folder contains roads.dbf without roads.shp — an orphaned "
        "sidecar file is flagged."
    ),
    "Файлы Roads.shp и roads.shp различаются только регистром — отмечается совпадение имён.": (
        "The files Roads.shp and roads.shp differ only by case — a name "
        "collision is flagged."
    ),
    "Длина полного пути {} символов — больше {} (ограничение Windows)": (
        "The full path is {} characters long — more than {} (Windows "
        "limit)"
    ),
    "Недопустимые символы в имени файла: {}": (
        "Invalid characters in the file name: {}"
    ),
    "Имя файла зарезервировано в Windows: {}": (
        "The file name is reserved in Windows: {}"
    ),
    "Имя файла заканчивается пробелом или точкой": (
        "The file name ends with a space or a dot"
    ),
    "Имена файлов различаются только регистром: {}": (
        "File names differ only by case: {}"
    ),
    "Осиротевший сопутствующий файл: {} — основной файл не найден": (
        "Orphaned sidecar file: {} — the main file was not found"
    ),
    "Уточнить систему координат и проверить СК": (
        "Refine CRS and check it"
    ),
    "Читает систему координат слоёв, обновляет колонку «Система координат» и отмечает отсутствующую, неизвестную или смешанную СК.": (
        "Reads the CRS of layers, updates the “CRS” column and flags "
        "missing, unknown or mixed CRS."
    ),
    "Проверка имён полей": "Field name check",
    "Проверяет нелатинские символы, длину имени (не более 10 символов DBF), пробелы, недопустимые символы и дубли после усечения.": (
        "Checks non-Latin characters, name length (10 characters max for "
        "DBF), spaces, invalid characters and duplicates after truncation."
    ),
    "Проверка заполненности атрибутов": "Attribute completeness check",
    "Проверяет NULL и пустые строки, долю заполнения по полям, обязательные поля и почти пустые слои.": (
        "Checks NULL and empty strings, per-field fill rates, required "
        "fields and almost empty layers."
    ),
    "Для каждого векторного слоя и таблицы ZGeo читает объекты и считает пустыми значения NULL и строки, состоящие только из пробелов. Для каждого поля вычисляется доля заполнения.": (
        "For each vector layer and table, ZGeo reads the features and "
        "treats NULL values and whitespace-only strings as empty. The fill "
        "rate is calculated for every field."
    ),
    "Поле считается обязательным, если для него задано ограничение NOT NULL или оно входит в первичный ключ слоя. Пустые значения в обязательных полях отмечаются отдельно.": (
        "A field is considered required if it has a NOT NULL constraint or "
        "belongs to the layer primary key. Empty values in required fields "
        "are reported separately."
    ),
    "Поля с заполненностью ниже 50% отмечаются как проблемы. Слой считается почти пустым, если заполнено менее 5% ячеек или не менее 95% объектов не содержат ни одного заполненного атрибута. В отчёт попадают доли заполнения по полям.": (
        "Fields with a fill rate below 50% are reported as problems. A "
        "layer is considered almost empty if less than 5% of cells are "
        "filled or at least 95% of features contain no filled attributes. "
        "Field fill rates are included in the report."
    ),
    "Поле name: 120 из 200 значений (60%) — проблемы нет, если поле не обязательное.": (
        "Field name: 120 of 200 values (60%) — no problem if the field is "
        "not required."
    ),
    "Обязательное поле code: 3 пустых значения — отмечается.": (
        "Required field code: 3 empty values — reported."
    ),
    "Слой из 1000 объектов, где 98% объектов не имеют атрибутов — отмечается как почти пустой.": (
        "A layer with 1000 features where 98% of features have no "
        "attributes — reported as almost empty."
    ),
    "Проверка набора данных": "Dataset integrity check",
    "Проверяет обязательные файлы набора, наличие .cpg и корректность указанной кодировки DBF.": (
        "Checks required dataset files, the presence of .cpg and the "
        "specified DBF encoding."
    ),
    "Проверка метаданных и CRS": "Metadata and CRS check",
    "Проверяет наличие .prj и .cpg у SHP, .aux.xml и .ovr у растров, файла привязки .tfw/.tifw/.wld при отсутствии CRS, а также устаревшие CRS, единицы и порядок осей.": (
        "Checks for .prj and .cpg on SHP, .aux.xml and .ovr on rasters, "
        "a .tfw/.tifw/.wld world file when no CRS is present, and also "
        "deprecated CRS, units and axis order."
    ),
    "Кольцо, у которого первая и последняя вершины не совпадают — отмечается «Незамкнутое кольцо».": (
        "A ring whose first and last vertices do not coincide — “Unclosed "
        "ring” is flagged."
    ),
    "Объект без геометрии — отмечается «Геометрия отсутствует (null)».": (
        "A feature without geometry — “Geometry is missing (null)” is "
        "flagged."
    ),
    "Итоги группируются по слою, а для найденных ошибок сохраняются номер объекта и место ошибки; подробно описывается до 1000 ошибок на слой.": (
        "Results are grouped by layer, and the feature number and the "
        "location of the error are saved for the found errors; up to "
        "1,000 errors per layer are described in detail."
    ),
    "Ищет NaN/Inf, слишком большие значения, перепутанные широту и долготу и координаты вне допустимого диапазона CRS.": (
        "Finds NaN/Inf, excessively large values, swapped latitude and "
        "longitude and coordinates outside the valid CRS range."
    ),
    "Для каждой вершины объекта координаты проверяются на NaN и бесконечность, на абсолютные значения больше 1e9, на перепутанные широту и долготу и на выход за диапазон CRS.": (
        "Every feature vertex is checked for NaN and infinity, for "
        "absolute values greater than 1e9, for swapped latitude and "
        "longitude, and for coordinates outside the CRS range."
    ),
    "Для географических систем координат долгота должна быть в пределах от -180 до 180, широта — от -90 до 90. Для проекционных систем вершина преобразуется в WGS 84 и проверяется попадание в границы системы координат.": (
        "For geographic coordinate systems the longitude must be within "
        "-180 to 180 and the latitude within -90 to 90. For projected "
        "systems the vertex is transformed to WGS 84 and checked against "
        "the bounds of the coordinate system."
    ),
    "Координата с абсолютным значением больше 1e9 — отмечается «Слишком большая координата».": (
        "A coordinate with an absolute value greater than 1e9 — "
        "“Excessively large coordinate” is flagged."
    ),
    "Нелатинское имя поля: {}": "Non-Latin field name: {}",
    "Слой «{}»: заполненность атрибутов {}% ({} из {} ячеек, пусто {}); низкая заполненность: {}; обязательные поля с пустыми значениями: {}": (
        "Layer “{}”: attribute fill {}% ({} of {} cells, {} empty); low "
        "fill: {}; required fields with empty values: {}"
    ),
    "Слой «{}»: почти пустые атрибуты — заполнено {} из {} ячеек ({}%), полностью пустых объектов {} из {} ({}%)": (
        "Layer “{}”: almost empty attributes — {} of {} cells filled "
        "({}%), {} of {} features completely empty ({}%)"
    ),
    "Обязательное поле «{}»: заполнено {} из {} ({}%), пусто {}": (
        "Required field “{}”: filled {} of {} ({}%), {} empty"
    ),
    "Поле «{}»: заполнено {} из {} ({}%), пусто {}": (
        "Field “{}”: filled {} of {} ({}%), {} empty"
    ),
    "Слой «{}»: наложений полигонов: {}, разрывов полигонов: {}, висячих линий: {} (свободных концов: {}), пересечений линий: {}, наложений линий: {}": (
        "Layer “{}”: polygon overlaps: {}, polygon gaps: {}, dangling "
        "lines: {} (free endpoints: {}), line intersections: {}, line "
        "overlaps: {}"
    ),
    "Наложение полигонов: объект {} и объект {} — площадь {}": (
        "Polygon overlap: feature {} and feature {} — area {}"
    ),
    "Разрыв полигонов: площадь {} — окружён объектами: {}": (
        "Polygon gap: area {} — surrounded by features: {}"
    ),
    "Висячая линия: объект {} — свободных концов: {}": (
        "Dangling line: feature {} — free endpoints: {}"
    ),
    "Наложение линий: объект {} и объект {} — длина {}": (
        "Line overlap: feature {} and feature {} — length {}"
    ),
    "Пересечение линий: объект {} и объект {}": (
        "Line intersection: feature {} and feature {}"
    ),
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
    "Время проверки": "Check timing",
    "Операция": "Operation",
    "Файлов": "Files",
    "Время": "Time",
    "Время, с": "Time, s",
    "Файлов/с": "Files/s",
    "Файлов/мин": "Files/min",
    "Статус": "Status",
    "Завершено": "Completed",
    "Прервано": "Interrupted",
    "Итого по папке": "Folder total",
    "менее 1 секунды": "less than 1 second",
    "секунда": "second",
    "секунды": "seconds",
    "секунд": "seconds",
    "минута": "minute",
    "минуты": "minutes",
    "минут": "minutes",
    "час": "hour",
    "часа": "hours",
    "часов": "hours",
    "Проверка JSON на формат GeoJSON": (
        "Check JSON for GeoJSON format"
    ),
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
    "Экспорт списка в HTML…": "Exporting list to HTML…",
    "{}_файлы.html": "{}_files.html",
    "Список экспортирован: {}": "List exported: {}",
    "Экспорт списка отменён": "List export cancelled",
    "ZGeo — экспорт данных": "ZGeo — data export",
    "Сформировано: {}": "Generated: {}",
    "Строк: {}": "Rows: {}",
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
