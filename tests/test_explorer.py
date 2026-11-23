import unittest
from pathlib import Path
from unittest.mock import patch

from zgeo.explorer import (
    _LINUX_OPEN,
    _MACOS_OPEN,
    _WINDOWS_EXPLORER,
    group_files_by_folder,
    open_file,
    open_folder,
)


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


class OpenFolderTests(unittest.TestCase):
    def test_opens_folder_with_platform_command(self) -> None:
        folder = Path("C:/data/out")
        cases = (
            ("win32", [_WINDOWS_EXPLORER, str(folder)]),
            ("darwin", [_MACOS_OPEN, str(folder)]),
            ("linux", [_LINUX_OPEN, str(folder)]),
        )

        for platform, expected in cases:
            with self.subTest(platform=platform):
                with patch(
                    "zgeo.explorer.subprocess.Popen"
                ) as popen, patch(
                    "zgeo.explorer.sys.platform", platform
                ):
                    errors = open_folder(folder)

                self.assertEqual(errors, [])
                self.assertEqual(popen.call_args.args[0], expected)

    def test_open_folder_error_is_reported(self) -> None:
        folder = Path("C:/data/out")
        with patch(
            "zgeo.explorer.subprocess.Popen",
            side_effect=OSError("boom"),
        ), patch("zgeo.explorer.sys.platform", "win32"):
            errors = open_folder(folder)

        self.assertEqual(len(errors), 1)
        self.assertIn(str(folder), errors[0])
        self.assertIn("boom", errors[0])


class OpenFileTests(unittest.TestCase):
    def test_windows_uses_default_application(self) -> None:
        path = Path("C:/data/roads.prj")
        with patch(
            "zgeo.explorer.os.startfile", create=True
        ) as startfile, patch(
            "zgeo.explorer.sys.platform", "win32"
        ):
            errors = open_file(path)

        self.assertEqual(errors, [])
        startfile.assert_called_once_with(str(path))

    def test_open_file_error_is_reported(self) -> None:
        path = Path("C:/data/roads.prj")
        with patch(
            "zgeo.explorer.os.startfile",
            side_effect=OSError("boom"),
            create=True,
        ), patch("zgeo.explorer.sys.platform", "win32"):
            errors = open_file(path)

        self.assertEqual(len(errors), 1)
        self.assertIn(str(path), errors[0])
        self.assertIn("boom", errors[0])
