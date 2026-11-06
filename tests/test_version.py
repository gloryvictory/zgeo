"""Проверки чтения версии плагина."""

from __future__ import annotations

import configparser
import unittest
from pathlib import Path

from zgeo.version import get_plugin_version

METADATA_PATH = Path(__file__).resolve().parents[1] / "metadata.txt"


class VersionTests(unittest.TestCase):
    def test_version_matches_metadata(self) -> None:
        parser = configparser.ConfigParser()
        parser.read(METADATA_PATH, encoding="utf-8")

        self.assertEqual(
            get_plugin_version(), parser.get("general", "version")
        )

    def test_version_is_not_unknown(self) -> None:
        self.assertNotEqual(get_plugin_version(), "неизвестна")


if __name__ == "__main__":
    unittest.main()
