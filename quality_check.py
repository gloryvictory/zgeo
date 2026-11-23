"""Проверки качества атрибутов, набора данных, слоёв и читаемости.

Модуль не зависит от QGIS: на вход подаются имена полей, системы
координат и количество объектов, собранные через провайдеры QGIS.
"""

from __future__ import annotations

import codecs
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .i18n import tr
from .scanner import FORMATS, RASTER

DBF_FIELD_NAME_LIMIT = 10
MAX_ABS_COORDINATE = 1e9
ATTRIBUTE_LOW_FILL_RATE = 0.5
ATTRIBUTE_ALMOST_EMPTY_RATE = 0.05
ATTRIBUTE_ALMOST_EMPTY_FEATURE_SHARE = 0.95

METRIC_UNITS = frozenset(
    {"Meters", "Kilometers", "Centimeters", "Millimeters"}
)
UNIT_SYMBOLS = {
    "Meters": "m",
    "Kilometers": "km",
    "Centimeters": "cm",
    "Millimeters": "mm",
    "Feet": "ft",
    "FeetUSSurvey": "ftUS",
    "Degrees": "°",
    "Unknown": "?",
}
RASTER_AUXILIARY_METADATA = (".aux.xml", ".ovr")
WORLD_FILE_EXTENSIONS = (".tfw", ".tifw", ".wld")
PRJ_EXTENSIONS = (".prj", ".qpj")
PRJ_ENCODINGS = ("utf-8-sig", "cp1251", "latin-1")
WKT_GEOGRAPHIC_ROOTS = frozenset(
    {"GEOGCS", "GEOGCRS", "GEODCRS", "GEOGRAPHICCRS"}
)
WKT_PROJECTED_ROOTS = frozenset(
    {
        "PROJCS",
        "PROJCRS",
        "PROJECTEDCRS",
        "ENGCRS",
        "ENGINEERINGCRS",
        "LOCAL_CS",
        "LOCALCRS",
    }
)
WKT_ROOT_NAMES = WKT_GEOGRAPHIC_ROOTS | WKT_PROJECTED_ROOTS | frozenset(
    {"COMPD_CS", "COMPOUNDCRS", "VERT_CS", "VERTCRS", "BOUNDCRS"}
)
EPSG_PATTERN = re.compile(
    r"""(?:AUTHORITY|ID)\s*\[\s*["']EPSG["']\s*,\s*["']?(\d+)["']?\s*\]""",
    re.IGNORECASE,
)

MAX_WINDOWS_PATH = 260
INVALID_NAME_CHARACTERS = frozenset('<>:"|?*')
RESERVED_NAME_STEMS = frozenset(
    {"con", "prn", "aux", "nul", "clock$"}
    | {"com{}".format(index) for index in range(1, 10)}
    | {"lpt{}".format(index) for index in range(1, 10)}
)
STEM_SIDECAR_PRIMARIES: Dict[str, Tuple[str, ...]] = {
    ".dbf": (".shp",),
    ".shx": (".shp",),
    ".qix": (".shp",),
    ".sbn": (".shp",),
    ".sbx": (".shp",),
    ".fbn": (".shp",),
    ".fbx": (".shp",),
    ".ain": (".shp",),
    ".aih": (".shp",),
    ".atx": (".shp",),
    ".ixs": (".shp",),
    ".mxs": (".shp",),
    ".fix": (".shp",),
    ".mid": (".mif",),
    ".dat": (".tab",),
    ".map": (".tab",),
    ".id": (".tab",),
    ".ind": (".tab",),
    ".csvt": (".csv",),
    ".hdr": (".bil", ".bsq", ".bip"),
}
GENERIC_SIDECAR_EXTENSIONS = frozenset(
    {".prj", ".cpg", ".tfw", ".wld", ".qml", ".sld"}
)
APPENDED_SIDECAR_SUFFIXES = (".aux.xml", ".ovr", ".xml")

REQUIRED_SIDECARS: Dict[str, Tuple[str, ...]] = {
    ".shp": (".dbf", ".shx"),
    ".mif": (".mid",),
    ".tab": (".dat", ".map", ".id"),
}

MISSING_CRS_VALUES = frozenset(
    {"", "—", "-", "Не определена", "Undefined", "Unknown", "Неизвестна"}
)


@dataclass(frozen=True)
class QualityIssue:
    """Одна найденная проблема."""

    check: str
    message: str
    args: Tuple[object, ...] = ()
    layer: str = ""
    feature_id: Optional[int] = None
    location: str = ""
    detail_only: bool = False
    feature_ids: Tuple[int, ...] = ()

    @property
    def all_feature_ids(self) -> Tuple[int, ...]:
        """Все объекты замечания — для выделения на карте."""

        ids: List[int] = []
        for feature_id in (self.feature_id, *self.feature_ids):
            if feature_id is None or feature_id in ids:
                continue
            ids.append(feature_id)
        return tuple(ids)


@dataclass(frozen=True)
class ReadabilityProblem:
    """Ошибка открытия или чтения файла/слоя."""

    kind: str
    layer: str = ""
    detail: str = ""


def readability_issues(
    problems: Sequence[ReadabilityProblem],
    check: str,
) -> List[QualityIssue]:
    """Преобразовать ошибки читаемости в замечания проверки."""

    issues: List[QualityIssue] = []
    for problem in problems:
        detail = problem.detail.strip()
        suffix = ": {}".format(detail) if detail else ""
        layer = problem.layer
        location = "Чтение"

        if problem.kind == "file_missing":
            message = "Файл не найден или недоступен"
            args: Tuple[object, ...] = ()
            location = "Файл"
        elif problem.kind == "empty_file":
            message = "Файл пуст (0 байт)"
            args = ()
            location = "Файл"
        elif problem.kind == "no_layers":
            message = "QGIS не смог открыть файл: нет доступных слоёв"
            args = ()
            location = "Файл"
        elif problem.kind == "open":
            message = "QGIS не смог открыть файл{}"
            args = (suffix,)
            location = "Файл"
        elif problem.kind == "vector_read":
            message = "Не удалось прочитать объект из слоя «{}»{}"
            args = (layer, suffix)
        elif problem.kind == "raster_read":
            message = "Не удалось прочитать данные растра «{}»{}"
            args = (layer, suffix)
        else:
            continue

        issues.append(
            QualityIssue(
                check,
                message,
                args,
                layer=layer,
                location=location,
            )
        )
    return issues


@dataclass(frozen=True)
class FieldFillStats:
    """Заполненность одного атрибутивного поля."""

    name: str
    total: int
    empty: int
    required: bool = False

    @property
    def filled(self) -> int:
        return max(self.total - self.empty, 0)

    @property
    def fill_rate(self) -> float:
        if self.total <= 0:
            return 0.0
        return self.filled / self.total


@dataclass(frozen=True)
class LayerFillStats:
    """Заполненность атрибутов одного векторного слоя."""

    layer: str
    feature_count: int
    fields: Tuple[FieldFillStats, ...]
    fully_empty_features: int = 0

    @property
    def total_cells(self) -> int:
        return max(self.feature_count, 0) * len(self.fields)

    @property
    def empty_cells(self) -> int:
        return sum(field.empty for field in self.fields)

    @property
    def filled_cells(self) -> int:
        return max(self.total_cells - self.empty_cells, 0)

    @property
    def fill_rate(self) -> float:
        if self.total_cells <= 0:
            return 0.0
        return self.filled_cells / self.total_cells

    @property
    def fully_empty_share(self) -> float:
        if self.feature_count <= 0:
            return 0.0
        return min(
            max(self.fully_empty_features / self.feature_count, 0.0),
            1.0,
        )



@dataclass(frozen=True)
class FieldControlStats:
    """Управляющие и невидимые символы в одном поле."""

    name: str
    features_with_chars: int
    characters: Tuple[str, ...] = ()
    example: str = ""
    feature_ids: Tuple[int, ...] = ()


@dataclass(frozen=True)
class LayerControlStats:
    """Найденные управляющие символы одного слоя."""

    layer: str
    feature_count: int
    fields: Tuple[FieldControlStats, ...]

    @property
    def affected_features(self) -> int:
        return max(
            (field.features_with_chars for field in self.fields),
            default=0,
        )

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.features_with_chars)






TEXT_LENGTH_DEVIATIONS = 3.0
TEXT_LENGTH_MIN_SAMPLES = 3


def length_statistics(lengths: Sequence[int]) -> Tuple[float, float]:
    """Вернуть среднее и стандартное отклонение длин значений."""

    if not lengths:
        return 0.0, 0.0
    count = len(lengths)
    mean = sum(lengths) / count
    variance = sum((length - mean) ** 2 for length in lengths) / count
    return mean, variance ** 0.5


def length_outlier_positions(
    lengths: Sequence[int],
    *,
    deviations: float = TEXT_LENGTH_DEVIATIONS,
    min_samples: int = TEXT_LENGTH_MIN_SAMPLES,
) -> Tuple[int, ...]:
    """Вернуть позиции значений длиннее среднего более чем на N отклонений."""

    if min_samples <= 0 or len(lengths) < min_samples:
        return ()
    mean, deviation = length_statistics(lengths)
    if deviation <= 0:
        return ()
    limit = mean + deviations * deviation
    return tuple(
        position
        for position, length in enumerate(lengths)
        if length > limit
    )



@dataclass(frozen=True)
class FieldDateRangeStats:
    """Даты вне разумного диапазона в одном поле."""

    name: str
    total: int
    invalid: Tuple[Tuple[int, str], ...] = ()
    earliest: int = 0
    latest: int = 0

    @property
    def feature_ids(self) -> Tuple[int, ...]:
        """Объекты с датой вне диапазона."""

        return tuple(
            feature_id for feature_id, _value in self.invalid
        )

    @property
    def count(self) -> int:
        return len(self.invalid)

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.count / self.total, 0.0), 1.0)


@dataclass(frozen=True)
class LayerDateRangeStats:
    """Даты вне разумного диапазона в одном слое."""

    layer: str
    feature_count: int
    fields: Tuple[FieldDateRangeStats, ...]

    @property
    def invalid_total(self) -> int:
        return sum(field.count for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.count)

@dataclass(frozen=True)
class FieldTextLengthStats:
    """Аномальная длина текста в одном текстовом поле."""

    name: str
    total: int
    outliers: Tuple[Tuple[int, int], ...] = ()
    mean: float = 0.0
    deviation: float = 0.0
    example: str = ""

    @property
    def count(self) -> int:
        return len(self.outliers)

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.count / self.total, 0.0), 1.0)

    @property
    def feature_ids(self) -> Tuple[int, ...]:
        """Объекты с аномальной длиной значения."""

        return tuple(
            feature_id for feature_id, _length in self.outliers
        )

    @property
    def longest(self) -> int:
        return max((length for _id, length in self.outliers), default=0)


@dataclass(frozen=True)
class LayerTextLengthStats:
    """Аномальная длина текста в одном слое."""

    layer: str
    feature_count: int
    fields: Tuple[FieldTextLengthStats, ...]

    @property
    def outlier_total(self) -> int:
        return sum(field.count for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.count)


@dataclass(frozen=True)
class FieldEncodingStats:
    """Текст в неверной кодировке в одном текстовом поле."""

    name: str
    total: int
    affected: int = 0
    example: str = ""
    repaired: str = ""
    feature_ids: Tuple[int, ...] = ()

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.affected / self.total, 0.0), 1.0)


@dataclass(frozen=True)
class LayerEncodingStats:
    """Текст в неверной кодировке в одном слое."""

    layer: str
    feature_count: int
    fields: Tuple[FieldEncodingStats, ...]

    @property
    def affected_total(self) -> int:
        return sum(field.affected for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.affected)

@dataclass(frozen=True)
class FieldNumericTextStats:
    """Числа, записанные как текст, в одном текстовом поле."""

    name: str
    total: int
    numeric: int
    integer: int = 0
    real: int = 0
    example: str = ""
    text: int = 0
    text_example: str = ""
    feature_ids: Tuple[int, ...] = ()
    text_feature_ids: Tuple[int, ...] = ()

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.numeric / self.total, 0.0), 1.0)

    @property
    def text_share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.text / self.total, 0.0), 1.0)


@dataclass(frozen=True)
class LayerNumericTextStats:
    """Числа, записанные как текст, в одном слое."""

    layer: str
    feature_count: int
    fields: Tuple[FieldNumericTextStats, ...]

    @property
    def numeric_total(self) -> int:
        return sum(field.numeric for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.numeric)

    @property
    def mixed_fields(self) -> Tuple[FieldNumericTextStats, ...]:
        return tuple(
            field for field in self.fields if field.numeric and field.text
        )

    @property
    def mixed_field_count(self) -> int:
        return len(self.mixed_fields)

@dataclass(frozen=True)
class FieldInnerSpaceStats:
    """Двойные пробелы внутри значений одного текстового поля."""

    name: str
    total: int
    affected: int
    example: str = ""
    feature_ids: Tuple[int, ...] = ()

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.affected / self.total, 0.0), 1.0)


@dataclass(frozen=True)
class LayerInnerSpaceStats:
    """Двойные пробелы внутри значений одного слоя."""

    layer: str
    feature_count: int
    fields: Tuple[FieldInnerSpaceStats, ...]

    @property
    def affected_total(self) -> int:
        return sum(field.affected for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.affected)

@dataclass(frozen=True)
class FieldEdgeSpaceStats:
    """Пробелы по краям значений в одном текстовом поле."""

    name: str
    total: int
    affected: int
    leading: int = 0
    trailing: int = 0
    example: str = ""
    feature_ids: Tuple[int, ...] = ()

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.affected / self.total, 0.0), 1.0)


@dataclass(frozen=True)
class LayerEdgeSpaceStats:
    """Пробелы по краям значений одного слоя."""

    layer: str
    feature_count: int
    fields: Tuple[FieldEdgeSpaceStats, ...]

    @property
    def affected_total(self) -> int:
        return sum(field.affected for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.affected)

@dataclass(frozen=True)
class FieldBlankStats:
    """Пустые строки в одном текстовом поле."""

    name: str
    total: int
    blank: int
    feature_ids: Tuple[int, ...] = ()

    @property
    def share(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(max(self.blank / self.total, 0.0), 1.0)


@dataclass(frozen=True)
class LayerBlankStats:
    """Пустые строки одного слоя."""

    layer: str
    feature_count: int
    fields: Tuple[FieldBlankStats, ...]

    @property
    def blank_total(self) -> int:
        return sum(field.blank for field in self.fields)

    @property
    def affected_fields(self) -> int:
        return sum(1 for field in self.fields if field.blank)

@dataclass
class TopologyStats:
    """Счётчики топологических проблем одного слоя."""

    layer: str
    polygon_overlaps: int = 0
    polygon_gaps: int = 0
    dangling_lines: int = 0
    free_ends: int = 0
    line_intersections: int = 0
    line_overlaps: int = 0

    @property
    def has_issues(self) -> bool:
        return bool(
            self.polygon_overlaps
            or self.polygon_gaps
            or self.dangling_lines
            or self.line_intersections
            or self.line_overlaps
        )


@dataclass(frozen=True)
class CrsDescriptor:
    """Сведения о системе координат слоя для проверки метаданных."""

    layer: str
    authid: str
    description: str
    valid: bool
    geographic: bool
    projected: bool
    deprecated: bool
    units: str
    axis_inverted: bool


@dataclass(frozen=True)
class PrjFileState:
    """Результат разбора файла .prj/.qpj."""

    status: str
    text: str = ""
    name: str = ""
    kind: str = ""
    epsg: str = ""
    detail: str = ""


def prj_kind_label(kind: str) -> str:
    """Вернуть переведённую подпись типа системы координат."""

    if kind == "geographic":
        return tr("географическая")
    if kind == "projected":
        return tr("проекционная")
    return tr("иная")


def invalid_name_characters(name: str) -> str:
    """Список недопустимых в Windows символов, найденных в имени."""

    found = {
        character
        for character in name
        if character in INVALID_NAME_CHARACTERS or ord(character) < 32
    }
    return "".join(sorted(found))


def is_reserved_file_name(name: str) -> bool:
    """Проверить зарезервированное в Windows имя файла."""

    return Path(name).stem.casefold() in RESERVED_NAME_STEMS


def has_trailing_space_or_dot(name: str) -> bool:
    """Проверить завершение имени точкой или пробелом."""

    return name.endswith((" ", "."))


def orphan_sidecars(files: Mapping[str, Path]) -> List[str]:
    """Вернуть сопутствующие файлы, у которых нет основного файла."""

    names = {name.casefold() for name in files}
    return [
        name for name in sorted(names) if _is_orphan_sidecar(name, names)
    ]


def _is_orphan_sidecar(name: str, names: set) -> bool:
    for suffix in APPENDED_SIDECAR_SUFFIXES:
        if not name.endswith(suffix) or len(name) <= len(suffix):
            continue
        primary = name[: -len(suffix)]
        if Path(primary).suffix in FORMATS:
            return primary not in names

    extension = Path(name).suffix
    if extension in STEM_SIDECAR_PRIMARIES:
        stem = name[: -len(extension)]
        primaries = STEM_SIDECAR_PRIMARIES[extension]
        return not any(stem + primary in names for primary in primaries)

    if extension in GENERIC_SIDECAR_EXTENSIONS:
        stem = name[: -len(extension)]
        return not any(
            Path(other).stem == stem and Path(other).suffix in FORMATS
            for other in names
        )

    return False


def file_path_issues(
    geo_file,
    files: Mapping[str, Path],
    *,
    names: Sequence[str] = (),
    folder_owner: bool = False,
) -> List[QualityIssue]:
    """Проверить длину пути, имя файла, коллизии и осиротевшие спутники."""

    path = geo_file.path
    issues: List[QualityIssue] = []

    length = len(str(path))
    if length > MAX_WINDOWS_PATH:
        issues.append(
            QualityIssue(
                "file_paths",
                "Длина полного пути {} символов — больше {} "
                "(ограничение Windows)",
                (length, MAX_WINDOWS_PATH),
                location="Путь",
            )
        )

    invalid = invalid_name_characters(path.name)
    if invalid:
        issues.append(
            QualityIssue(
                "file_paths",
                "Недопустимые символы в имени файла: {}",
                (invalid,),
                location="Имя файла",
            )
        )

    if is_reserved_file_name(path.name):
        issues.append(
            QualityIssue(
                "file_paths",
                "Имя файла зарезервировано в Windows: {}",
                (path.name,),
                location="Имя файла",
            )
        )

    if has_trailing_space_or_dot(path.name):
        issues.append(
            QualityIssue(
                "file_paths",
                "Имя файла заканчивается пробелом или точкой",
                location="Имя файла",
            )
        )

    group = sorted(
        name for name in names if name.casefold() == path.name.casefold()
    )
    if len(group) > 1 and path.name == group[0]:
        issues.append(
            QualityIssue(
                "file_paths",
                "Имена файлов различаются только регистром: {}",
                (", ".join(group),),
                location="Имя файла",
            )
        )

    if folder_owner:
        for orphan in orphan_sidecars(files):
            issues.append(
                QualityIssue(
                    "file_paths",
                    "Осиротевший сопутствующий файл: {} — основной "
                    "файл не найден",
                    (orphan,),
                    location=orphan,
                    detail_only=True,
                )
            )

    return issues


def directory_names(
    directory: Path, cache: Dict[str, Tuple[str, ...]]
) -> Tuple[str, ...]:
    """Вернуть имена файлов каталога в исходном регистре."""

    key = str(directory)
    names = cache.get(key)
    if names is None:
        try:
            names = tuple(
                sorted(
                    entry.name
                    for entry in directory.iterdir()
                    if entry.is_file()
                )
            )
        except OSError:
            names = ()
        cache[key] = names
    return names


def directory_files(
    directory: Path, cache: Dict[str, Dict[str, Path]]
) -> Dict[str, Path]:
    """Вернуть файлы каталога по именам в нижнем регистре."""

    key = str(directory)
    files = cache.get(key)
    if files is None:
        try:
            files = {
                item.name.casefold(): item
                for item in directory.iterdir()
                if item.is_file()
            }
        except OSError:
            files = {}
        cache[key] = files
    return files


def completeness_issues(
    geo_file, files: Mapping[str, Path]
) -> List[QualityIssue]:
    """Проверить наличие обязательных файлов набора данных."""

    required = REQUIRED_SIDECARS.get(geo_file.extension)
    if not required:
        return []

    base = geo_file.path.stem.casefold()
    missing = [
        extension
        for extension in required
        if base + extension not in files
    ]
    if not missing:
        return []

    return [
        QualityIssue(
            "dataset_completeness",
            "В наборе отсутствуют файлы: {}",
            (", ".join(missing),),
            location=", ".join(missing),
        )
    ]


def dbf_encoding_issues(
    geo_file, files: Mapping[str, Path]
) -> List[QualityIssue]:
    """Проверить наличие .cpg и корректность указанной кодировки DBF."""

    if geo_file.extension != ".shp":
        return []

    base = geo_file.path.stem.casefold()
    dbf_path = files.get(base + ".dbf")
    if dbf_path is None:
        return []

    issues: List[QualityIssue] = []
    cpg_path = files.get(base + ".cpg")

    if _dbf_ldid(dbf_path) is None:
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Не удалось прочитать заголовок DBF",
                location="DBF",
            )
        )

    if cpg_path is None:
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Нет файла .cpg: кодировка DBF не указана",
                location=".cpg",
            )
        )
        return issues

    try:
        content = cpg_path.read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        try:
            content = cpg_path.read_bytes().decode("latin-1").strip()
        except OSError:
            content = ""

    if not content:
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Файл .cpg пуст: кодировка DBF не указана",
                location=".cpg",
            )
        )
    elif not is_known_encoding(content):
        issues.append(
            QualityIssue(
                "dbf_encoding",
                "Неизвестная кодировка в .cpg: {}",
                (content,),
                location=".cpg",
            )
        )

    return issues


def metadata_sidecar_issues(
    geo_file,
    files: Mapping[str, Path],
    *,
    has_crs: bool = True,
    include_cpg: bool = True,
    include_prj: bool = True,
) -> List[QualityIssue]:
    """Проверить наличие обязательных и вспомогательных файлов метаданных."""

    issues: List[QualityIssue] = []
    base = geo_file.path.stem.casefold()

    if geo_file.extension == ".shp":
        if include_prj and not any(
            base + extension in files
            for extension in PRJ_EXTENSIONS
        ):
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "В наборе отсутствует файл метаданных: {}",
                    (".prj",),
                    location=".prj",
                )
            )
        if include_cpg and base + ".cpg" not in files:
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "В наборе отсутствует файл метаданных: {}",
                    (".cpg",),
                    location=".cpg",
                )
            )
        return issues

    if geo_file.category != RASTER:
        return issues

    missing = [
        extension
        for extension in RASTER_AUXILIARY_METADATA
        if base + extension not in files
    ]
    if missing:
        issues.append(
            QualityIssue(
                "metadata_crs",
                "Нет вспомогательных метаданных: {}",
                (", ".join(missing),),
                location=", ".join(missing),
            )
        )

    if not has_crs and not any(
        base + extension in files
        for extension in WORLD_FILE_EXTENSIONS
    ):
        issues.append(
            QualityIssue(
                "metadata_crs",
                "Нет файла привязки .tfw/.tifw/.wld: "
                "растровая привязка не найдена",
                location=".tfw",
            )
        )

    return issues


def is_known_encoding(value: str) -> bool:
    """Проверить, что строка .cpg задаёт известную кодировку."""

    text = value.strip()
    if not text:
        return False

    upper = text.upper()
    if upper.startswith("LDID/"):
        try:
            ldid = int(upper.split("/", 1)[1])
        except ValueError:
            return False
        return 0 <= ldid <= 255

    candidate = text
    if candidate.isdigit():
        candidate = "cp" + candidate
    try:
        codecs.lookup(candidate)
    except LookupError:
        return False
    return True


def _dbf_ldid(path: Path) -> Optional[int]:
    """Прочитать байт языкового драйвера из заголовка DBF."""

    try:
        with path.open("rb") as handle:
            header = handle.read(32)
    except OSError:
        return None
    if len(header) < 32:
        return None
    return header[29]



NULL_LIKE_FIELD_NAMES = frozenset(
    {"null", "none", "nan", "<null>", "nil", "undefined", "null_null"}
)
FILLER_FIELD_PREFIXES = (
    "unnamed",
    "attribute",
    "column",
    "field",
    "attr",
    "col",
)

SUSPICIOUS_FIELD_REASONS = frozenset(
    {"empty", "null", "filler", "numeric"}
)


def suspicious_field_name_reason(name: str) -> str:
    """Вернуть причину подозрительного имени поля или пустую строку.

    Подозрительными считаются пустое имя, имена, обозначающие отсутствие
    значения (NULL, None, NAN), технические имена после импорта вида
    «Field1», «field_2», «Unnamed: 0», «Column3» и имена из одних цифр.
    """

    text = (name or "").strip()
    if not text:
        return "empty"

    folded = text.casefold()
    if folded in NULL_LIKE_FIELD_NAMES:
        return "null"

    if folded.replace(" ", "").replace("_", "").replace("-", "").isdigit():
        return "numeric"

    for prefix in FILLER_FIELD_PREFIXES:
        if not folded.startswith(prefix):
            continue
        tail = folded[len(prefix):].strip(" _-:.")
        if not tail or tail.isdigit():
            return "filler"
    return ""


def suspicious_field_name_issues(
    layers: Sequence[Tuple[str, Sequence[str]]],
) -> List[QualityIssue]:
    """Найти технические и бессмысленные имена полей в слоях."""

    issues: List[QualityIssue] = []

    for layer_name, field_names in layers:
        empty_index = 0
        for name in field_names:
            reason = suspicious_field_name_reason(name)
            if not reason:
                continue
            if reason == "empty":
                empty_index += 1
                shown = "—"
                location = "Поле {}".format(empty_index)
            else:
                shown = name
                location = name
            issues.append(
                QualityIssue(
                    "suspicious_field_names",
                    "Слой «{}»: подозрительное имя поля «{}» — {}",
                    (
                        layer_name,
                        shown,
                        _suspicious_reason_label(reason),
                    ),
                    layer=layer_name,
                    location=location,
                )
            )

    return issues


def _suspicious_reason_label(reason: str) -> str:
    """Текст причины подозрительного имени поля."""

    if reason == "null":
        return tr("имя обозначает отсутствующее значение")
    if reason == "numeric":
        return tr("имя состоит только из цифр")
    if reason == "filler":
        return tr("техническое имя после импорта")
    return tr("имя поля пустое")

def field_name_issues(
    layers: Sequence[Tuple[str, Sequence[str]]],
) -> List[QualityIssue]:
    """Проверить длину, пробелы и спецсимволы в именах полей."""

    issues: List[QualityIssue] = []
    seen_names = set()

    for layer_name, field_names in layers:
        for name in field_names:
            if not name or name in seen_names:
                continue
            seen_names.add(name)

            if len(name) > DBF_FIELD_NAME_LIMIT:
                issues.append(
                    QualityIssue(
                        "shp_field_names",
                        "Поле «{}»: длина {} больше {} символов "
                        "(ограничение DBF)",
                        (name, len(name), DBF_FIELD_NAME_LIMIT),
                        layer=layer_name,
                        location=name,
                    )
                )

            if " " in name:
                issues.append(
                    QualityIssue(
                        "shp_field_names",
                        "Поле «{}»: содержит пробел",
                        (name,),
                        layer=layer_name,
                        location=name,
                    )
                )

            special = "".join(
                sorted(
                    {
                        character
                        for character in name
                        if character != " "
                        and not (character.isalnum() or character == "_")
                    }
                )
            )
            if special:
                issues.append(
                    QualityIssue(
                        "shp_field_names",
                        "Поле «{}»: недопустимые символы: {}",
                        (name, special),
                        layer=layer_name,
                        location=name,
                    )
                )

    return issues


def case_insensitive_duplicate_issues(
    layers: Sequence[Tuple[str, Sequence[str]]],
) -> List[QualityIssue]:
    """Найти имена полей, совпадающие без учёта регистра в одном слое."""

    issues: List[QualityIssue] = []

    for layer_name, field_names in layers:
        groups: Dict[str, List[str]] = {}
        for name in field_names:
            if not name:
                continue
            groups.setdefault(name.casefold(), []).append(name)

        for key, names in groups.items():
            if len(names) < 2:
                continue
            unique = sorted(set(names), key=str.casefold)
            issues.append(
                QualityIssue(
                    "field_name_duplicates",
                    "Слой «{}»: имена полей совпадают без учёта регистра: {}",
                    (layer_name, ", ".join(unique)),
                    layer=layer_name,
                    location=key,
                )
            )

    return issues


def truncated_duplicate_issues(
    layers: Sequence[Tuple[str, Sequence[str]]],
) -> List[QualityIssue]:
    """Найти имена полей, совпадающие после усечения до лимита DBF."""

    issues: List[QualityIssue] = []

    for layer_name, field_names in layers:
        groups: Dict[str, List[str]] = {}
        for name in field_names:
            if not name:
                continue
            key = name[:DBF_FIELD_NAME_LIMIT].casefold()
            groups.setdefault(key, []).append(name)

        for names in groups.values():
            unique = sorted(set(names))
            if len(unique) < 2:
                continue
            issues.append(
                QualityIssue(
                    "truncated_duplicates",
                    "Слой «{}»: после усечения до {} символов совпадают "
                    "имена полей: {}",
                    (layer_name, DBF_FIELD_NAME_LIMIT, ", ".join(unique)),
                    layer=layer_name,
                    location=key,
                )
            )

    return issues


def prj_state(path: Path) -> "PrjFileState":
    """Прочитать .prj и разобрать WKT без привязки к QGIS."""

    try:
        raw = path.read_bytes()
    except OSError as error:
        return PrjFileState("unreadable", detail=str(error))

    text = _decode_prj(raw)
    stripped = text.strip()
    if not stripped:
        return PrjFileState("empty")

    info = _wkt_info(stripped)
    if info is None:
        return PrjFileState("invalid", text=stripped, detail=_snippet(stripped))
    kind, name, epsg = info
    return PrjFileState(
        "ok",
        text=stripped,
        name=name,
        kind=kind,
        epsg=epsg,
    )


def prj_file_issues(
    geo_file,
    files: Mapping[str, Path],
    descriptors: Sequence[CrsDescriptor] = (),
) -> List[QualityIssue]:
    """Проверить наличие, читаемость .prj и согласованность с CRS слоёв."""

    base = geo_file.path.stem.casefold()
    prj_path = files.get(base + ".prj")
    qpj_path = files.get(base + ".qpj")
    path = prj_path or qpj_path

    if path is None:
        return [
            QualityIssue(
                "prj_file",
                "Нет файла .prj: система координат слоя не закреплена",
                location=".prj",
            )
        ]

    state = prj_state(path)
    if state.status == "unreadable":
        return [
            QualityIssue(
                "prj_file",
                "Не удалось прочитать файл .prj: {}",
                (path.name,),
                location=path.name,
            )
        ]
    if state.status == "empty":
        return [
            QualityIssue(
                "prj_file",
                "Файл .prj пуст: система координат не указана",
                location=path.name,
            )
        ]
    if state.status == "invalid":
        return [
            QualityIssue(
                "prj_file",
                "Файл .prj не содержит корректного WKT: {}",
                (state.detail,),
                location=path.name,
            )
        ]

    issues: List[QualityIssue] = []
    comparable = [
        descriptor
        for descriptor in descriptors
        if descriptor.valid and _crs_kind(descriptor)
    ]

    mismatched_kind = [
        descriptor
        for descriptor in comparable
        if _crs_kind(descriptor) != state.kind
    ]
    if comparable and len(mismatched_kind) == len(comparable):
        descriptor = mismatched_kind[0]
        issues.append(
            QualityIssue(
                "prj_file",
                "Тип системы координат в .prj не совпадает с CRS слоя: "
                "в .prj {}, у слоя {}",
                (
                    prj_kind_label(state.kind),
                    prj_kind_label(_crs_kind(descriptor)),
                ),
                layer=descriptor.layer,
                location=path.name,
            )
        )

    authid_layers = [
        descriptor
        for descriptor in descriptors
        if descriptor.valid
        and descriptor.authid.upper().startswith("EPSG:")
    ]
    if state.epsg and authid_layers:
        code = state.epsg
        mismatched_epsg = [
            descriptor
            for descriptor in authid_layers
            if descriptor.authid.split(":", 1)[1].strip() != code
        ]
        if len(mismatched_epsg) == len(authid_layers):
            descriptor = mismatched_epsg[0]
            issues.append(
                QualityIssue(
                    "prj_file",
                    "Файл .prj не соответствует CRS слоя: в .prj EPSG:{}, "
                    "у слоя {}",
                    (code, descriptor.authid),
                    layer=descriptor.layer,
                    location=path.name,
                )
            )

    return issues


def _decode_prj(raw: bytes) -> str:
    for encoding in PRJ_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _snippet(text: str, limit: int = 60) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1] + "…"


def _wkt_info(text: str) -> Optional[Tuple[str, str, str]]:
    """Вернуть тип, имя и код EPSG из WKT или None, если WKT некорректен."""

    if text.count("[") != text.count("]") or text.count("(") != text.count(")"):
        return None
    root = _wkt_root(text)
    if root not in WKT_ROOT_NAMES:
        return None
    if root in WKT_GEOGRAPHIC_ROOTS:
        kind = "geographic"
    elif root in WKT_PROJECTED_ROOTS:
        kind = "projected"
    else:
        kind = ""
    codes = EPSG_PATTERN.findall(text)
    return kind, _wkt_name(text), codes[-1] if codes else ""


def _wkt_root(text: str) -> str:
    match = re.match(r"\s*([A-Za-z_][A-Za-z_0-9]*)", text)
    return match.group(1).upper() if match else ""


def _wkt_name(text: str) -> str:
    match = re.search(r"""["']([^"']+)["']""", text)
    return match.group(1) if match else ""


def _crs_kind(descriptor: CrsDescriptor) -> str:
    if descriptor.projected:
        return "projected"
    if descriptor.geographic:
        return "geographic"
    return ""


def duplicate_geometry_issues(
    layer_name: str,
    entries: Sequence[Tuple[int, object]],
    *,
    max_detail: int = 1000,
) -> List[QualityIssue]:
    """Найти объекты с полностью совпадающей геометрией.

    entries — пары «идентификатор объекта, ключ геометрии»; ключом служит
    WKB, поэтому совпадают только полностью одинаковые геометрии.
    """

    seen: Dict[object, int] = {}
    counts: Dict[object, int] = {}
    details: List[QualityIssue] = []
    duplicates = 0

    for feature_id, key in entries:
        counts[key] = counts.get(key, 0) + 1
        original = seen.get(key)
        if original is None:
            seen[key] = feature_id
            continue
        duplicates += 1
        if len(details) < max_detail:
            details.append(
                QualityIssue(
                    "duplicate_features",
                    "Дубль геометрии объекта {} — совпадает с объектом {}",
                    (feature_id, original),
                    layer=layer_name,
                    feature_id=feature_id,
                    location="Геометрия",
                    detail_only=True,
                )
            )

    if not duplicates:
        return []

    groups = sum(1 for value in counts.values() if value > 1)
    details.append(
        QualityIssue(
            "duplicate_features",
            "Слой «{}»: дублей по геометрии: {}, групп: {}",
            (layer_name, duplicates, groups),
            layer=layer_name,
            location="Геометрия",
        )
    )
    return details


def crs_issues(values: Sequence[str]) -> List[QualityIssue]:
    """Найти отсутствующие, неизвестные или смешанные системы координат."""

    defined = [value for value in values if value]
    if not defined:
        return []

    missing = [
        value for value in defined if value in MISSING_CRS_VALUES
    ]
    unique = {
        value for value in defined if value not in MISSING_CRS_VALUES
    }

    if not unique:
        return [
            QualityIssue(
                "crs_quality",
                "Система координат не определена",
                location="Система координат",
            )
        ]

    issues: List[QualityIssue] = []
    if missing:
        issues.append(
            QualityIssue(
                "crs_quality",
                "У части слоёв не определена система координат",
                location="Система координат",
            )
        )

    if len(unique) > 1:
        examples = ", ".join(sorted(unique)[:3])
        issues.append(
            QualityIssue(
                "crs_quality",
                "Смешанные системы координат: {}",
                (examples,),
                location="Система координат",
            )
        )

    return issues


def crs_metadata_issues(
    descriptors: Sequence[CrsDescriptor],
    *,
    include_missing: bool = True,
) -> List[QualityIssue]:
    """Проверить устаревшие CRS, единицы и порядок осей."""

    issues: List[QualityIssue] = []

    for descriptor in descriptors:
        layer = descriptor.layer
        if not descriptor.valid:
            if include_missing:
                issues.append(
                    QualityIssue(
                        "metadata_crs",
                        "Слой «{}»: система координат не определена",
                        (layer,),
                        layer=layer,
                        location="Система координат",
                    )
                )
            continue

        if descriptor.deprecated:
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "Слой «{}»: устаревшая система координат {} — {}",
                    (
                        layer,
                        descriptor.authid or "—",
                        descriptor.description or "—",
                    ),
                    layer=layer,
                    location="Система координат",
                )
            )

        if not descriptor.authid:
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "Слой «{}»: система координат без кода EPSG/авторитета",
                    (layer,),
                    layer=layer,
                    location="Система координат",
                )
            )

        unit_label = UNIT_SYMBOLS.get(
            descriptor.units, descriptor.units
        )
        if descriptor.projected and descriptor.units not in METRIC_UNITS:
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "Слой «{}»: не метрические единицы CRS: {}",
                    (layer, unit_label),
                    layer=layer,
                    location="Единицы CRS",
                )
            )
        elif (
            descriptor.geographic
            and descriptor.units != "Degrees"
        ):
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "Слой «{}»: для географической CRS ожидаются "
                    "градусы, указано: {}",
                    (layer, unit_label),
                    layer=layer,
                    location="Единицы CRS",
                )
            )

        if descriptor.projected and descriptor.axis_inverted:
            issues.append(
                QualityIssue(
                    "metadata_crs",
                    "Слой «{}»: нестандартный порядок осей CRS (YX)",
                    (layer,),
                    layer=layer,
                    location="Порядок осей",
                )
            )

    return issues


def coordinate_problem(
    x: float,
    y: float,
    *,
    geographic: bool,
    max_abs: float = MAX_ABS_COORDINATE,
) -> Optional[str]:
    """Классифицировать проблему координаты без привязки к QGIS.

    Возвращает ``non_finite``, ``huge``, ``swapped`` или
    ``out_of_range``. Для географических координат предполагается
    традиционный порядок QGIS: x — долгота, y — широта.
    """

    if not math.isfinite(x) or not math.isfinite(y):
        return "non_finite"
    if abs(x) > max_abs or abs(y) > max_abs:
        return "huge"

    if geographic:
        if abs(x) <= 90.0 and 90.0 < abs(y) <= 180.0:
            return "swapped"
        if not (-180.0 <= x <= 180.0 and -90.0 <= y <= 90.0):
            return "out_of_range"

    return None


def empty_field_issues(
    layers: Sequence[LayerFillStats],
) -> List[QualityIssue]:
    """Найти поля, у которых все значения пустые (100% NULL)."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        for field in layer.fields:
            if field.total <= 0 or field.empty < field.total:
                continue
            issues.append(
                QualityIssue(
                    "empty_fields",
                    "Поле «{}»: 100% пустых значений "
                    "(NULL или пустые строки) — {} из {}",
                    (field.name, field.empty, field.total),
                    layer=layer.layer,
                    location=field.name,
                )
            )

    return issues


def attribute_fill_issues(
    layers: Sequence[LayerFillStats],
    *,
    low_fill_rate: float = ATTRIBUTE_LOW_FILL_RATE,
    almost_empty_rate: float = ATTRIBUTE_ALMOST_EMPTY_RATE,
    almost_empty_feature_share: float = (
        ATTRIBUTE_ALMOST_EMPTY_FEATURE_SHARE
    ),
) -> List[QualityIssue]:
    """Проверить NULL/пустые значения и долю заполнения атрибутов."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0 or not layer.fields:
            continue
        if layer.total_cells <= 0:
            continue

        required_empty = [
            field
            for field in layer.fields
            if field.required and field.empty > 0
        ]
        low_fields = [
            field
            for field in layer.fields
            if (
                not field.required
                and field.empty > 0
                and field.fill_rate < low_fill_rate
            )
        ]
        almost_empty = (
            layer.fill_rate < almost_empty_rate
            or layer.fully_empty_share >= almost_empty_feature_share
        )

        if not required_empty and not low_fields and not almost_empty:
            continue

        low_text = _fill_field_list(low_fields)
        required_text = _fill_field_names(required_empty)
        issues.append(
            QualityIssue(
                "attribute_fill",
                "Слой «{}»: заполненность атрибутов {}% "
                "({} из {} ячеек, пусто {}); низкая заполненность: {}; "
                "обязательные поля с пустыми значениями: {}",
                (
                    layer.layer,
                    _fill_percent(layer.fill_rate),
                    layer.filled_cells,
                    layer.total_cells,
                    layer.empty_cells,
                    low_text,
                    required_text,
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        if almost_empty:
            issues.append(
                QualityIssue(
                    "attribute_fill",
                    "Слой «{}»: почти пустые атрибуты — заполнено {} "
                    "из {} ячеек ({}%), полностью пустых объектов {} "
                    "из {} ({}%)",
                    (
                        layer.layer,
                        layer.filled_cells,
                        layer.total_cells,
                        _fill_percent(layer.fill_rate),
                        layer.fully_empty_features,
                        layer.feature_count,
                        _fill_percent(layer.fully_empty_share),
                    ),
                    layer=layer.layer,
                    location="Атрибуты",
                )
            )

        for field in layer.fields:
            if field.required:
                message = (
                    "Обязательное поле «{}»: заполнено {} из {} "
                    "({}%), пусто {}"
                )
            else:
                message = (
                    "Поле «{}»: заполнено {} из {} ({}%), пусто {}"
                )
            issues.append(
                QualityIssue(
                    "attribute_fill",
                    message,
                    (
                        field.name,
                        field.filled,
                        field.total,
                        _fill_percent(field.fill_rate),
                        field.empty,
                    ),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues









def date_range_issues(
    layers: Sequence[LayerDateRangeStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить поля с датами вне разумного диапазона."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        affected_fields = [
            field for field in layer.fields if field.count
        ]
        if not affected_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.count,
                field.total,
            )
            for field in affected_fields[:field_limit]
        ]
        if len(affected_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "date_range",
                "Слой «{}»: даты вне разумного диапазона — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(affected_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in affected_fields:
            ids = ", ".join(
                str(feature_id)
                for feature_id, _value in field.invalid[:10]
            )
            values = ", ".join(
                "«{}»".format(value) for _id, value in field.invalid[:5]
            )
            issues.append(
                QualityIssue(
                    "date_range",
                    "Поле «{}»: даты вне разумного диапазона у {} из {} "
                    "объектов ({}%); годы от {} до {} (объекты: {}); "
                    "значения: {}",
                    (
                        field.name,
                        field.count,
                        field.total,
                        _fill_percent(field.share),
                        field.earliest,
                        field.latest,
                        ids,
                        values,
                    ),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues

def text_length_issues(
    layers: Sequence[LayerTextLengthStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить текстовые поля со значениями аномальной длины."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        affected_fields = [
            field for field in layer.fields if field.count
        ]
        if not affected_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.count,
                field.total,
            )
            for field in affected_fields[:field_limit]
        ]
        if len(affected_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "text_length",
                "Слой «{}»: аномальная длина текста — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(affected_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in affected_fields:
            ids = ", ".join(
                str(feature_id)
                for feature_id, _length in field.outliers[:10]
            )
            args: List[object] = [
                field.name,
                field.count,
                field.total,
                _fill_percent(field.share),
                round(field.mean, 1),
                round(field.deviation, 1),
                field.longest,
                ids,
            ]
            message = (
                "Поле «{}»: значения аномальной длины у {} из {} "
                "объектов ({}%); среднее {}, отклонение {}, самая длинная "
                "{} символов (объекты: {})"
            )
            if field.example:
                message = message + "; пример: {}"
                args.append(field.example)
            issues.append(
                QualityIssue(
                    "text_length",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                    feature_ids=field.feature_ids,
                )
            )

    return issues


def text_encoding_issues(
    layers: Sequence[LayerEncodingStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить поля с текстом в неверной кодировке."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        affected_fields = [
            field for field in layer.fields if field.affected
        ]
        if not affected_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.affected,
                field.total,
            )
            for field in affected_fields[:field_limit]
        ]
        if len(affected_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "text_encoding",
                "Слой «{}»: текст в неверной кодировке — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(affected_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in affected_fields:
            args: List[object] = [
                field.name,
                field.affected,
                field.total,
                _fill_percent(field.share),
                field.example,
            ]
            message = (
                "Поле «{}»: текст в неверной кодировке у {} из {} "
                "объектов ({}%); пример: «{}»"
            )
            if field.repaired:
                message = message + ", исправляется на «{}»"
                args.append(field.repaired)
            issues.append(
                QualityIssue(
                    "text_encoding",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues

def numeric_text_issues(
    layers: Sequence[LayerNumericTextStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить текстовые поля, где значения записаны числами."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        numeric_fields = [
            field for field in layer.fields if field.numeric
        ]
        if not numeric_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.numeric,
                field.total,
            )
            for field in numeric_fields[:field_limit]
        ]
        if len(numeric_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "numeric_text",
                "Слой «{}»: числа, записанные как текст — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(numeric_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in numeric_fields:
            args: List[object] = [
                field.name,
                field.numeric,
                field.total,
                _fill_percent(field.share),
                field.integer,
                field.real,
            ]
            message = (
                "Поле «{}»: числа, записанные как текст, у {} из {} "
                "объектов ({}%); целых {}, дробных {}"
            )
            if field.example:
                message = message + "; пример: «{}»"
                args.append(field.example)
            issues.append(
                QualityIssue(
                    "numeric_text",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues


def mixed_type_issues(
    layers: Sequence[LayerNumericTextStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить текстовые поля, где смешаны числа и текст."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        mixed_fields = list(layer.mixed_fields)
        if not mixed_fields:
            continue

        parts = [
            tr(
                "{} — числа {}, текст {}",
                field.name,
                field.numeric,
                field.text,
            )
            for field in mixed_fields[:field_limit]
        ]
        if len(mixed_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "mixed_types",
                "Слой «{}»: смешанные типы в поле — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(mixed_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in mixed_fields:
            args: List[object] = [
                field.name,
                field.numeric,
                _fill_percent(field.share),
                field.text,
                _fill_percent(field.text_share),
                field.total,
            ]
            message = (
                "Поле «{}»: смешанные типы — числа: {} ({}%), "
                "текст: {} ({}%) из {} объектов"
            )
            if field.example and field.text_example:
                message = message + "; примеры: «{}» и «{}»"
                args.extend([field.example, field.text_example])
            issues.append(
                QualityIssue(
                    "mixed_types",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                    feature_ids=field.feature_ids,
                )
            )

    return issues


def inner_space_issues(
    layers: Sequence[LayerInnerSpaceStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить текстовые поля с двойными пробелами внутри значений."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        affected_fields = [
            field for field in layer.fields if field.affected
        ]
        if not affected_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.affected,
                field.total,
            )
            for field in affected_fields[:field_limit]
        ]
        if len(affected_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "inner_spaces",
                "Слой «{}»: двойные пробелы внутри значений — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(affected_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in affected_fields:
            args: List[object] = [
                field.name,
                field.affected,
                field.total,
                _fill_percent(field.share),
            ]
            message = (
                "Поле «{}»: двойные пробелы внутри значений у {} из {} "
                "объектов ({}%)"
            )
            if field.example:
                message = message + "; пример: {}"
                args.append(field.example)
            issues.append(
                QualityIssue(
                    "inner_spaces",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues

def edge_space_issues(
    layers: Sequence[LayerEdgeSpaceStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить текстовые поля со пробелами по краям значений."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        affected_fields = [
            field for field in layer.fields if field.affected
        ]
        if not affected_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.affected,
                field.total,
            )
            for field in affected_fields[:field_limit]
        ]
        if len(affected_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "edge_spaces",
                "Слой «{}»: пробелы по краям значений — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(affected_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in affected_fields:
            args: List[object] = [
                field.name,
                field.affected,
                field.total,
                _fill_percent(field.share),
                field.leading,
                field.trailing,
            ]
            message = (
                "Поле «{}»: пробелы по краям у {} из {} объектов ({}%); "
                "в начале {}, в конце {}"
            )
            if field.example:
                message = message + "; пример: {}"
                args.append(field.example)
            issues.append(
                QualityIssue(
                    "edge_spaces",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues

def blank_string_issues(
    layers: Sequence[LayerBlankStats],
    *,
    field_limit: int = 8,
) -> List[QualityIssue]:
    """Отметить текстовые поля с пустыми строками вместо NULL."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        blank_fields = [field for field in layer.fields if field.blank]
        if not blank_fields:
            continue

        parts = [
            tr(
                "{} — {} из {}",
                field.name,
                field.blank,
                field.total,
            )
            for field in blank_fields[:field_limit]
        ]
        if len(blank_fields) > field_limit:
            parts.append("…")
        issues.append(
            QualityIssue(
                "blank_strings",
                "Слой «{}»: пустые строки вместо NULL — "
                "затронуто полей {} из {}: {}",
                (
                    layer.layer,
                    len(blank_fields),
                    len(layer.fields),
                    ", ".join(parts),
                ),
                layer=layer.layer,
                location="Атрибуты",
            )
        )

        for field in blank_fields:
            issues.append(
                QualityIssue(
                    "blank_strings",
                    "Поле «{}»: пустые строки у {} из {} объектов ({}%)",
                    (
                        field.name,
                        field.blank,
                        field.total,
                        _fill_percent(field.share),
                    ),
                    layer=layer.layer,
                    location=field.name,
                    detail_only=True,
                )
            )

    return issues

def control_character_issues(
    layers: Sequence[LayerControlStats],
    *,
    character_limit: int = 6,
) -> List[QualityIssue]:
    """Отметить поля с управляющими и невидимыми символами."""

    issues: List[QualityIssue] = []

    for layer in layers:
        if layer.feature_count <= 0:
            continue
        for field in layer.fields:
            if field.features_with_chars <= 0:
                continue
            characters = field.characters[:character_limit]
            names = ", ".join(characters)
            if len(field.characters) > character_limit:
                names = names + ", …"
            args: List[object] = [
                layer.layer,
                field.name,
                field.features_with_chars,
                layer.feature_count,
                names,
            ]
            message = (
                "Слой «{}»: в поле «{}» управляющие или невидимые "
                "символы найдены у {} из {} объектов: {}"
            )
            if field.example:
                message = message + "; пример: «{}»"
                args.append(field.example)
            issues.append(
                QualityIssue(
                    "control_chars",
                    message,
                    tuple(args),
                    layer=layer.layer,
                    location=field.name,
                )
            )

    return issues

def _fill_percent(value: float) -> int:
    return int(round(max(min(value, 1.0), 0.0) * 100))


def _fill_field_list(fields: Sequence[FieldFillStats]) -> str:
    if not fields:
        return "—"
    limit = 8
    parts = [
        f"{field.name} — {_fill_percent(field.fill_rate)}%"
        for field in fields[:limit]
    ]
    if len(fields) > limit:
        parts.append("…")
    return ", ".join(parts)


def _fill_field_names(fields: Sequence[FieldFillStats]) -> str:
    if not fields:
        return "—"
    limit = 8
    names = [field.name for field in fields[:limit]]
    if len(fields) > limit:
        names.append("…")
    return ", ".join(names)


def topology_summary_issues(
    stats: TopologyStats,
) -> List[QualityIssue]:
    """Сформировать сводку топологических проблем слоя."""

    if not stats.has_issues:
        return []

    return [
        QualityIssue(
            "topology",
            "Слой «{}»: наложений полигонов: {}, разрывов полигонов: {}, "
            "висячих линий: {} (свободных концов: {}), пересечений "
            "линий: {}, наложений линий: {}",
            (
                stats.layer,
                stats.polygon_overlaps,
                stats.polygon_gaps,
                stats.dangling_lines,
                stats.free_ends,
                stats.line_intersections,
                stats.line_overlaps,
            ),
            layer=stats.layer,
            location="Топология",
        )
    ]





def combined_duplicate_issues(
    layer_name: str,
    entries: Sequence[Tuple[int, object]],
    *,
    max_detail: int = 1000,
) -> List[QualityIssue]:
    """Найти объекты, у которых совпадают и атрибуты, и геометрия.

    entries — пары «идентификатор объекта, ключ»; ключом служит пара из
    значений всех атрибутов и WKB геометрии, поэтому совпадают только
    объекты с одинаковыми атрибутами и одинаковой геометрией.
    """

    seen: Dict[object, int] = {}
    counts: Dict[object, int] = {}
    details: List[QualityIssue] = []
    duplicates = 0

    for feature_id, key in entries:
        counts[key] = counts.get(key, 0) + 1
        original = seen.get(key)
        if original is None:
            seen[key] = feature_id
            continue
        duplicates += 1
        if len(details) < max_detail:
            details.append(
                QualityIssue(
                    "duplicate_combined",
                    "Дубль по атрибутам и геометрии: объект {} "
                    "совпадает с объектом {}",
                    (feature_id, original),
                    layer=layer_name,
                    feature_id=feature_id,
                    location="Атрибуты и геометрия",
                    detail_only=True,
                )
            )

    if not duplicates:
        return []

    groups = sum(1 for value in counts.values() if value > 1)
    details.append(
        QualityIssue(
            "duplicate_combined",
            "Слой «{}»: дублей по атрибутам и геометрии: {}, групп: {}",
            (layer_name, duplicates, groups),
            layer=layer_name,
            location="Атрибуты и геометрия",
        )
    )
    return details
