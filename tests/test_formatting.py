import unittest

from zgeo.formatting import format_size


class FormatSizeTests(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(format_size(0), "0 Б")
        self.assertEqual(format_size(1), "1 Б")
        self.assertEqual(format_size(1023), "1023 Б")

    def test_kilobytes(self):
        self.assertEqual(format_size(1024), "1 КБ")
        self.assertEqual(format_size(1536), "1.5 КБ")
        self.assertEqual(format_size(10 * 1024), "10 КБ")
        self.assertEqual(format_size(100 * 1024), "100 КБ")

    def test_larger_units(self):
        self.assertEqual(format_size(1024 ** 2), "1 МБ")
        self.assertEqual(format_size(1024 ** 3), "1 ГБ")
        self.assertEqual(format_size(1024 ** 4), "1 ТБ")
        self.assertEqual(format_size(1024 ** 5), "1024 ТБ")
