"""Проверка соответствия расширения файла и его содержимого.

Модуль не зависит от QGIS: читаются первые байты файла и сравниваются с
сигнатурами известных форматов. Пустые и слишком короткие файлы
проверкой не считаются — для них есть проверка читаемости.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .i18n import tr
from .quality_check import QualityIssue
from .scanner import GeoFile

HEADER_SIZE = 4096

SHP_MAGIC = b"\x00\x00\x27\x0a"
SQLITE_MAGIC = b"SQLite format 3\x00"
ZIP_MAGICS = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
TIFF_MAGICS = (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+")
OLE2_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
PARQUET_MAGIC = b"PAR1"
ARROW_MAGIC = b"ARROW1"
FLATGEOBUF_MAGIC = b"fgb\x03"
PMTILES_MAGIC = b"PMTiles"
NETCDF_MAGICS = (b"CDF\x01", b"CDF\x02")
HDF5_MAGIC = b"\x89HDF\r\n\x1a\n"
HDF4_MAGIC = b"\x0e\x03\x13\x01"
JP2_MAGIC = b"\x00\x00\x00\x0cjP  \r\n\x87\n"
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
JPEG_MAGIC = b"\xff\xd8\xff"
PDF_MAGIC = b"%PDF-"
GZIP_MAGIC = b"\x1f\x8b"
EXECUTABLE_MAGICS = (b"MZ", b"\x7fELF")

CONTENT_SQLITE = "sqlite"
CONTENT_ZIP = "zip"
CONTENT_TIFF = "tiff"
CONTENT_SHAPEFILE = "shapefile"
CONTENT_OLE2 = "ole2"
CONTENT_PARQUET = "parquet"
CONTENT_ARROW = "arrow"
CONTENT_FLATGEOBUF = "flatgeobuf"
CONTENT_PMTILES = "pmtiles"
CONTENT_NETCDF = "netcdf"
CONTENT_HDF5 = "hdf5"
CONTENT_HDF4 = "hdf4"
CONTENT_JP2 = "jp2"
CONTENT_IMAGE = "image"
CONTENT_PDF = "pdf"
CONTENT_ARCHIVE = "archive"
CONTENT_EXECUTABLE = "executable"
CONTENT_JSON = "json"
CONTENT_XML = "xml"
CONTENT_TEXT = "text"
CONTENT_BINARY = "binary"

CONTENT_LABELS: Dict[str, str] = {
    CONTENT_SQLITE: "база SQLite",
    CONTENT_ZIP: "ZIP-архив",
    CONTENT_TIFF: "растровое изображение TIFF",
    CONTENT_SHAPEFILE: "файл Shapefile",
    CONTENT_OLE2: "документ OLE2 (старый формат Microsoft Office)",
    CONTENT_PARQUET: "файл Parquet",
    CONTENT_ARROW: "файл Arrow",
    CONTENT_FLATGEOBUF: "файл FlatGeobuf",
    CONTENT_PMTILES: "архив PMTiles",
    CONTENT_NETCDF: "файл NetCDF",
    CONTENT_HDF5: "файл HDF5",
    CONTENT_HDF4: "файл HDF4",
    CONTENT_JP2: "изображение JPEG 2000",
    CONTENT_IMAGE: "изображение",
    CONTENT_PDF: "документ PDF",
    CONTENT_ARCHIVE: "сжатый архив",
    CONTENT_EXECUTABLE: "исполняемый файл",
    CONTENT_JSON: "текст JSON",
    CONTENT_XML: "текст XML",
    CONTENT_TEXT: "текст",
    CONTENT_BINARY: "двоичные данные неизвестного формата",
}

XML_EXTENSIONS = frozenset(
    {".gml", ".kml", ".gpx", ".osm", ".vrt", ".svg"}
)
JSON_EXTENSIONS = frozenset(
    {".json", ".geojson", ".geojsonl", ".ndjson"}
)
TEXT_EXTENSIONS = frozenset(
    {".csv", ".tsv", ".mif", ".tab", ".asc", ".dxf", ".dem", ".hgt"}
)

EXPECTED_CONTENT: Dict[str, Tuple[str, ...]] = {
    ".shp": (CONTENT_SHAPEFILE,),
    ".gpkg": (CONTENT_SQLITE,),
    ".sqlite": (CONTENT_SQLITE,),
    ".spatialite": (CONTENT_SQLITE,),
    ".mbtiles": (CONTENT_SQLITE,),
    ".kmz": (CONTENT_ZIP,),
    ".xlsx": (CONTENT_ZIP,),
    ".xls": (CONTENT_OLE2,),
    ".tif": (CONTENT_TIFF,),
    ".tiff": (CONTENT_TIFF,),
    ".cog": (CONTENT_TIFF,),
    ".jp2": (CONTENT_JP2,),
    ".nc": (CONTENT_NETCDF, CONTENT_HDF5, CONTENT_HDF4),
    ".hdf": (CONTENT_HDF4, CONTENT_HDF5),
    ".h5": (CONTENT_HDF5,),
    ".parquet": (CONTENT_PARQUET,),
    ".arrow": (CONTENT_ARROW,),
    ".fgb": (CONTENT_FLATGEOBUF,),
    ".pmtiles": (CONTENT_PMTILES,),
    ".json": (CONTENT_JSON,),
    ".geojson": (CONTENT_JSON,),
    ".geojsonl": (CONTENT_JSON,),
    ".ndjson": (CONTENT_JSON,),
    ".gml": (CONTENT_XML,),
    ".kml": (CONTENT_XML,),
    ".gpx": (CONTENT_XML,),
    ".osm": (CONTENT_XML,),
    ".vrt": (CONTENT_XML,),
    ".csv": (CONTENT_TEXT, CONTENT_JSON),
    ".tsv": (CONTENT_TEXT, CONTENT_JSON),
    ".mif": (CONTENT_TEXT,),
    ".tab": (CONTENT_TEXT,),
    ".asc": (CONTENT_TEXT,),
    ".dxf": (CONTENT_TEXT,),
}


def detect_content_kind(path: Path) -> str:
    """Определить вид содержимого файла по первым байтам."""

    try:
        with Path(path).open("rb") as handle:
            header = handle.read(HEADER_SIZE)
    except OSError:
        return ""

    if not header:
        return ""

    if header.startswith(SQLITE_MAGIC):
        return CONTENT_SQLITE
    if header.startswith(SHP_MAGIC):
        return CONTENT_SHAPEFILE
    if header.startswith(FLATGEOBUF_MAGIC):
        return CONTENT_FLATGEOBUF
    if header.startswith(PMTILES_MAGIC):
        return CONTENT_PMTILES
    if header.startswith(HDF5_MAGIC):
        return CONTENT_HDF5
    if header.startswith(NETCDF_MAGICS):
        return CONTENT_NETCDF
    if header.startswith(JP2_MAGIC):
        return CONTENT_JP2
    if header.startswith(OLE2_MAGIC):
        return CONTENT_OLE2
    if header.startswith(PARQUET_MAGIC):
        return CONTENT_PARQUET
    if header.startswith(ARROW_MAGIC):
        return CONTENT_ARROW
    if header.startswith(HDF4_MAGIC):
        return CONTENT_HDF4
    if header.startswith(TIFF_MAGICS):
        return CONTENT_TIFF
    if header.startswith(ZIP_MAGICS):
        return CONTENT_ZIP
    if header.startswith(PNG_MAGIC) or header.startswith(JPEG_MAGIC):
        return CONTENT_IMAGE
    if header.startswith(PDF_MAGIC):
        return CONTENT_PDF
    if header.startswith(GZIP_MAGIC):
        return CONTENT_ARCHIVE
    if header.startswith(EXECUTABLE_MAGICS):
        return CONTENT_EXECUTABLE

    text = _decode_text(header)
    if text is None:
        return CONTENT_BINARY
    stripped = text.lstrip("\ufeff \t\r\n")
    if stripped.startswith(("{", "[")):
        return CONTENT_JSON
    if stripped.startswith("<"):
        return CONTENT_XML
    return CONTENT_TEXT


def _decode_text(header: bytes) -> Optional[str]:
    """Расшифровать начало файла как текст, если это возможно."""

    if b"\x00" in header:
        return None
    for encoding in ("utf-8-sig", "cp1251", "latin-1"):
        try:
            text = header.decode(encoding)
        except UnicodeDecodeError:
            continue
        if not any(
            not (character.isprintable() or character in "\r\n\t")
            for character in text
        ):
            return text
    return None


def content_kind_label(kind: str) -> str:
    """Название вида содержимого для отчёта."""

    return tr(CONTENT_LABELS.get(kind, CONTENT_LABELS[CONTENT_BINARY]))


def content_mismatch_issues(
    geo_file: GeoFile,
    kind: str,
    check: str = "content_mismatch",
) -> List[QualityIssue]:
    """Собрать замечание о несоответствии расширения и содержимого."""

    return [
        QualityIssue(
            check,
            "Файл «{}»: расширение {} не соответствует содержимому — "
            "в файле {}",
            (
                Path(geo_file.path).name,
                Path(geo_file.path).suffix.lower(),
                content_kind_label(kind),
            ),
            location="Содержимое",
        )
    ]


def inspect_content_mismatch(
    geo_file: GeoFile,
    check: str,
) -> Tuple[List[QualityIssue], bool]:
    """Проверить, что содержимое файла соответствует его расширению."""

    path = Path(geo_file.path)
    expected = EXPECTED_CONTENT.get(path.suffix.lower())
    if not expected:
        return [], False
    if not path.exists():
        return [], False

    kind = detect_content_kind(path)
    if not kind:
        return [], False

    if kind in expected:
        return [], True

    return content_mismatch_issues(geo_file, kind, check), True
