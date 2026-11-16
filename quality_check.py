"""Проверки качества атрибутов, набора данных и слоёв.

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


def empty_layer_issues(
    layers: Sequence[Tuple[str, int]],
) -> List[QualityIssue]:
    """Найти пустые слои и файлы без объектов."""

    if not layers:
        return []

    empty = [
        (name, count) for name, count in layers if count == 0
    ]
    if not empty:
        return []

    issues: List[QualityIssue] = []
    if len(empty) == len(layers):
        issues.append(
            QualityIssue(
                "empty_layers",
                "Файл не содержит объектов",
                location="Файл",
            )
        )

    for name, _count in empty:
        issues.append(
            QualityIssue(
                "empty_layers",
                "Слой «{}» не содержит объектов",
                (name,),
                layer=name,
                location="Слой",
            )
        )

    return issues
