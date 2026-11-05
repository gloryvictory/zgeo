import unittest
from pathlib import Path

from zgeo.explorer import group_files_by_folder


class GroupFilesByFolderTests(unittest.TestCase):
    def test_groups_files_by_parent_and_keeps_order(self):
        files = [
            Path("C:/data/one/a.shp"),
            Path("C:/data/two/b.gpkg"),
            Path("C:/data/one/c.tif"),
            Path("C:/data/two/d.geojson"),
        ]

        groups = group_files_by_folder(files)

        self.assertEqual(
            list(groups),
            [Path("C:/data/one"), Path("C:/data/two")],
        )
        self.assertEqual(
            [path.name for path in groups[Path("C:/data/one")]],
            ["a.shp", "c.tif"],
        )
        self.assertEqual(
            [path.name for path in groups[Path("C:/data/two")]],
            ["b.gpkg", "d.geojson"],
        )

    def test_empty_iterable(self):
        self.assertEqual(group_files_by_folder([]), {})
