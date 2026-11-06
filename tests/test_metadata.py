"""Проверки метаданных плагина."""

from __future__ import annotations

import configparser
import unittest
from pathlib import Path

METADATA_PATH = Path(__file__).resolve().parents[1] / "metadata.txt"


class MetadataTests(unittest.TestCase):
    def test_qgis_maximum_version_covers_qgis_4(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(METADATA_PATH, encoding="utf-8")

        self.assertEqual(
            parser.get("general", "qgisMinimumVersion"), "3.16"
        )
        self.assertTrue(
            parser.get("general", "qgisMaximumVersion").startswith("4.")
        )


if __name__ == "__main__":
    unittest.main()
