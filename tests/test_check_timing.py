import unittest

from zgeo.check_timing import TimingRecord, build_timing_rows
from zgeo.i18n import LANGUAGE_EN, LANGUAGE_RU, set_language


class CheckTimingTests(unittest.TestCase):
    def setUp(self) -> None:
        set_language(LANGUAGE_RU)

    def tearDown(self) -> None:
        set_language(LANGUAGE_RU)

    def test_record_speeds(self) -> None:
        record = TimingRecord("Проверка", 120, 2.0)

        self.assertEqual(record.files_per_second, 60.0)
        self.assertEqual(record.files_per_minute, 3600.0)
        self.assertEqual(record.status, "Завершено")

    def test_zero_values_have_no_speed(self) -> None:
        no_files = TimingRecord("Проверка", 0, 2.0)
        no_time = TimingRecord("Проверка", 10, 0.0)

        self.assertIsNone(no_files.files_per_second)
        self.assertIsNone(no_files.files_per_minute)
        self.assertIsNone(no_time.files_per_second)
        self.assertIsNone(no_time.files_per_minute)

    def test_rows_with_total(self) -> None:
        records = [
            TimingRecord("Проверки", 100, 2.0),
            TimingRecord("JSON", 25, 0.5, False),
        ]

        rows = build_timing_rows(
            records,
            total_files=120,
            total_seconds=2.5,
            completed=False,
        )

        self.assertEqual(rows[0], ["Проверки", 100, 2.0, 50.0, 3000.0, "Завершено"])
        self.assertEqual(rows[1][5], "Прервано")
        self.assertEqual(rows[2], ["", "", "", "", "", ""])
        self.assertEqual(
            rows[3],
            ["Итого по папке", 120, 2.5, 48.0, 2880.0, "Прервано"],
        )

    def test_rows_without_total_and_zero_speed(self) -> None:
        records = [
            TimingRecord("Проверки", 0, 1.0),
            TimingRecord("JSON", 10, 0.0),
        ]

        rows = build_timing_rows(records)

        self.assertEqual(rows[0][3], "—")
        self.assertEqual(rows[0][4], "—")
        self.assertEqual(rows[1][3], "—")
        self.assertEqual(rows[1][4], "—")
        self.assertEqual(len(rows), 2)

    def test_english_status(self) -> None:
        set_language(LANGUAGE_EN)
        rows = build_timing_rows(
            [TimingRecord("Check", 10, 1.0, False)],
            total_files=10,
            total_seconds=1.0,
            completed=False,
        )

        self.assertEqual(rows[0][5], "Interrupted")
        self.assertEqual(rows[-1][0], "Folder total")
        self.assertEqual(rows[-1][5], "Interrupted")


if __name__ == "__main__":
    unittest.main()
