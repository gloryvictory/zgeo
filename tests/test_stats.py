from __future__ import annotations

import unittest
from pathlib import Path

from zgeo.scanner import GeoFile, FormatInfo
from zgeo.stats import GIB, MIB, build_size_distribution, build_type_distribution


def make_file(name: str, size: int, format_name: str, category: str) -> GeoFile:
    return GeoFile(
        path=Path(name),
        relative_path=Path(name),
        format=FormatInfo(format_name, category),
        size=size,
    )


class SizeDistributionTests(unittest.TestCase):
    def test_bucket_boundaries(self) -> None:
        files = [
            make_file("a.shp", 0, "Shapefile", "vector"),
            make_file("b.shp", 500 * 1024, "Shapefile", "vector"),
            make_file("c.gpkg", MIB, "GeoPackage", "vector"),
            make_file("d.tif", 5 * MIB, "GeoTIFF / TIFF", "raster"),
            make_file("e.tif", 10 * MIB, "GeoTIFF / TIFF", "raster"),
            make_file("f.tif", 100 * MIB, "GeoTIFF / TIFF", "raster"),
            make_file("g.tif", GIB, "GeoTIFF / TIFF", "raster"),
            make_file("h.tif", 2 * GIB, "GeoTIFF / TIFF", "raster"),
        ]

        buckets = build_size_distribution(files)

        self.assertEqual(
            [bucket.count for bucket in buckets], [2, 2, 1, 1, 2]
        )
        self.assertEqual(buckets[0].total_size, 500 * 1024)
        self.assertEqual(buckets[4].total_size, 3 * GIB)

    def test_empty_distribution_keeps_all_buckets(self) -> None:
        buckets = build_size_distribution([])

        self.assertEqual(len(buckets), 5)
        self.assertTrue(all(bucket.count == 0 for bucket in buckets))


class TypeDistributionTests(unittest.TestCase):
    def test_grouping_and_sorting(self) -> None:
        files = [
            make_file("1.gpkg", 10, "GeoPackage", "vector"),
            make_file("2.shp", 20, "Shapefile", "vector"),
            make_file("3.shp", 30, "Shapefile", "vector"),
            make_file("4.tif", 40, "GeoTIFF / TIFF", "raster"),
        ]

        stats = build_type_distribution(files)

        self.assertEqual(
            [(item.name, item.count, item.total_size) for item in stats],
            [
                ("Shapefile", 2, 50),
                ("GeoTIFF / TIFF", 1, 40),
                ("GeoPackage", 1, 10),
            ],
        )

    def test_limit_groups_remaining_formats(self) -> None:
        files = [
            make_file(f"a{index}.shp", 1, "Shapefile", "vector")
            for index in range(5)
        ]
        files.extend(
            make_file(f"b{index}.gpkg", 2, "GeoPackage", "vector")
            for index in range(3)
        )
        files.extend(
            make_file(f"c{index}.tif", 3, "GeoTIFF / TIFF", "raster")
            for index in range(2)
        )
        files.append(make_file("d.csv", 4, "CSV", "table"))

        stats = build_type_distribution(files, limit=3)

        self.assertEqual(
            [item.name for item in stats],
            ["Shapefile", "GeoPackage", "Другие форматы"],
        )
        self.assertEqual(stats[-1].count, 3)
        self.assertEqual(stats[-1].total_size, 10)
        self.assertEqual(
            stats[-1].formats, ("GeoTIFF / TIFF", "CSV")
        )

    def test_empty_type_distribution(self) -> None:
        self.assertEqual(build_type_distribution([]), [])


if __name__ == "__main__":
    unittest.main()
