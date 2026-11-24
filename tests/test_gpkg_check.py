"""Проверки целостности GeoPackage и SQLite."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from zgeo.gpkg_check import (
    SQLITE_EXTENSIONS,
    _table_columns,
    _table_names,
    inspect_gpkg_integrity,
)


def geo_file(path: Path):
    return SimpleNamespace(path=path, extension=path.suffix.lower())


def make_database(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(str(path))


def make_gpkg(
    path: Path,
    *,
    contents=(("points", "features", 4326),),
    geometry=(("points", "geom", "POINT", 4326),),
    srs_ids=(4326,),
    feature_columns=("fid INTEGER PRIMARY KEY", "geom BLOB"),
) -> None:
    connection = make_database(path)
    try:
        connection.execute(
            "CREATE TABLE gpkg_spatial_ref_sys (srs_id INTEGER PRIMARY KEY)"
        )
        connection.executemany(
            "INSERT INTO gpkg_spatial_ref_sys (srs_id) VALUES (?)",
            [(value,) for value in srs_ids],
        )
        connection.execute(
            "CREATE TABLE gpkg_contents ("
            "table_name TEXT, data_type TEXT, srs_id INTEGER)"
        )
        connection.executemany(
            "INSERT INTO gpkg_contents "
            "(table_name, data_type, srs_id) VALUES (?, ?, ?)",
            contents,
        )
        connection.execute(
            "CREATE TABLE gpkg_geometry_columns ("
            "table_name TEXT, column_name TEXT, "
            "geometry_type_name TEXT, srs_id INTEGER)"
        )
        connection.executemany(
            "INSERT INTO gpkg_geometry_columns "
            "(table_name, column_name, geometry_type_name, srs_id) "
            "VALUES (?, ?, ?, ?)",
            geometry,
        )
        if feature_columns:
            connection.execute(
                "CREATE TABLE points ({})".format(
                    ", ".join(feature_columns)
                )
            )
        connection.commit()
    finally:
        connection.close()


class GpkgIntegrityTests(unittest.TestCase):
    def messages(self, path: Path) -> list:
        issues, applicable = inspect_gpkg_integrity(
            geo_file(path), "gpkg_integrity"
        )
        self.assertTrue(applicable)
        return [
            issue.message.format(*issue.args)
            for issue in issues
        ]

    def test_extensions(self) -> None:
        self.assertEqual(
            SQLITE_EXTENSIONS,
            frozenset({".gpkg", ".sqlite", ".spatialite"}),
        )

    def test_non_sqlite_file_is_not_applicable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roads.shp"
            path.write_bytes(b"x")
            issues, applicable = inspect_gpkg_integrity(
                geo_file(path), "gpkg_integrity"
            )
            self.assertFalse(applicable)
            self.assertEqual(issues, [])

    def test_valid_gpkg_has_no_issues(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "valid.gpkg"
            make_gpkg(path)
            self.assertEqual(self.messages(path), [])

    def test_missing_required_tables(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "empty.gpkg"
            connection = make_database(path)
            connection.execute("CREATE TABLE other (id INTEGER)")
            connection.commit()
            connection.close()
            messages = self.messages(path)
            for table in (
                "gpkg_contents",
                "gpkg_geometry_columns",
                "gpkg_spatial_ref_sys",
            ):
                self.assertIn(
                    "В GeoPackage отсутствует обязательная таблица: {}".format(
                        table
                    ),
                    messages,
                )

    def test_sqlite_without_gpkg_tables_is_checked_only_for_integrity(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plain.sqlite"
            connection = make_database(path)
            connection.execute("CREATE TABLE data (id INTEGER PRIMARY KEY)")
            connection.commit()
            connection.close()
            self.assertEqual(self.messages(path), [])

    def test_foreign_key_violation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fk.gpkg"
            make_gpkg(path)
            connection = make_database(path)
            connection.execute(
                "CREATE TABLE parent (id INTEGER PRIMARY KEY)"
            )
            connection.execute(
                "CREATE TABLE child ("
                "id INTEGER PRIMARY KEY, "
                "parent_id INTEGER REFERENCES parent(id))"
            )
            connection.execute(
                "INSERT INTO child (id, parent_id) VALUES (1, 999)"
            )
            connection.commit()
            connection.close()
            issues, applicable = inspect_gpkg_integrity(
                geo_file(path), "gpkg_integrity"
            )
            self.assertTrue(applicable)
            self.assertTrue(
                any(
                    issue.message.format(*issue.args).startswith(
                        "Нарушение внешнего ключа:"
                    )
                    for issue in issues
                ),
                issues,
            )

    def test_srs_missing_from_spatial_ref_sys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "srs.gpkg"
            make_gpkg(
                path,
                contents=(("points", "features", 9999),),
                geometry=(("points", "geom", "POINT", 9999),),
                srs_ids=(4326,),
            )
            self.assertTrue(
                any(
                    "srs_id 9999 отсутствует в gpkg_spatial_ref_sys"
                    in message
                    for message in self.messages(path)
                )
            )

    def test_srs_mismatch_between_contents_and_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mismatch.gpkg"
            make_gpkg(
                path,
                contents=(("points", "features", 4326),),
                geometry=(("points", "geom", "POINT", 3857),),
                srs_ids=(4326, 3857),
            )
            self.assertTrue(
                any(
                    "Несовпадение srs_id для таблицы points" in message
                    for message in self.messages(path)
                )
            )

    def test_geometry_column_missing_in_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "column.gpkg"
            make_gpkg(
                path,
                feature_columns=("fid INTEGER PRIMARY KEY",),
            )
            self.assertTrue(
                any(
                    "в таблице points нет такой колонки" in message
                    for message in self.messages(path)
                )
            )

    def test_feature_table_without_geometry_columns_row(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "geom.gpkg"
            make_gpkg(path, geometry=())
            self.assertTrue(
                any(
                    "Для таблицы points нет записи в gpkg_geometry_columns"
                    in message
                    for message in self.messages(path)
                )
            )

    def test_contents_table_missing_from_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.gpkg"
            make_gpkg(path)
            connection = make_database(path)
            connection.execute("DROP TABLE points")
            connection.commit()
            connection.close()
            self.assertTrue(
                any(
                    "Таблица points из gpkg_contents отсутствует в базе"
                    in message
                    for message in self.messages(path)
                )
            )

    def test_corrupt_file_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.gpkg"
            path.write_bytes(b"this is not a sqlite database")
            messages = self.messages(path)
            self.assertTrue(messages)
            self.assertTrue(
                any(
                    message.startswith("Проверка целостности SQLite:")
                    or message.startswith("Не удалось открыть SQLite:")
                    for message in messages
                ),
                messages,
            )

    def test_empty_and_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            empty = Path(directory) / "empty.sqlite"
            empty.write_bytes(b"")
            self.assertEqual(
                self.messages(empty),
                ["Файл пуст (0 байт)"],
            )
            missing = Path(directory) / "missing.sqlite"
            self.assertEqual(
                self.messages(missing),
                ["Файл не найден или недоступен"],
            )

    def test_table_read_error_is_not_silent(self) -> None:
        class BrokenConnection:
            def execute(self, _query, *_args):
                raise sqlite3.Error("disk I/O error")

        self.assertIsNone(_table_names(BrokenConnection()))
        self.assertIsNone(_table_columns(BrokenConnection(), "points"))


if __name__ == "__main__":
    unittest.main()
