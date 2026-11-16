import unittest

from zgeo.check_timing import (
    TimingRecord,
    build_timing_rows,
    format_duration,
)
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

    def test_human_readable_duration(self) -> None:
        self.assertEqual(format_duration(0), "0 секунд")
        self.assertEqual(format_duration(0.5), "менее 1 секунды")
        self.assertEqual(format_duration(21), "21 секунда")
        self.assertEqual(format_duration(22), "22 секунды")
        self.assertEqual(format_duration(25), "25 секунд")
        self.assertEqual(format_duration(45), "45 секунд")
        self.assertEqual(format_duration(60), "1 минута")
        self.assertEqual(format_duration(165), "2 минуты 45 секунд")
        self.assertEqual(
            format_duration(3661),
            "1 час 1 минута 1 секунда",
        )
        self.assertEqual(format_duration(7200), "2 часа")

    def test_human_readable_duration_english(self) -> None:
        set_language(LANGUAGE_EN)
        self.assertEqual(format_duration(0), "0 seconds")
        self.assertEqual(format_duration(0.5), "less than 1 second")
        self.assertEqual(format_duration(60), "1 minute")
        self.assertEqual(format_duration(165), "2 minutes 45 seconds")
        self.assertEqual(
            format_duration(3661),
            "1 hour 1 minute 1 second",
        )

    def test_rows_with_total(self) -> None:
        records = [
            TimingRecord("Проверки", 100, 2.0),
            TimingRecord("JSON", 25, 0.5, False),
        ]

        rows = build_timing_rows(
            records,
            total_files=120,
            total_seconds=2.6,
            completed=False,
        )

        self.assertEqual(
            rows[0],
            ["Проверки", 100, "2 секунды", 50.0, 3000.0, "Завершено"],
        )
        self.assertEqual(rows[1][2], "менее 1 секунды")
        self.assertEqual(rows[1][5], "Прервано")
        self.assertEqual(rows[2], ["", "", "", "", "", ""])
        self.assertEqual(
            rows[3],
            [
                "Итого по папке",
                120,
                "3 секунды",
                46.15,
                2769.23,
                "Прервано",
            ],
        )

    def test_rows_without_total_and_zero_speed(self) -> None:
        records = [
            TimingRecord("Проверки", 0, 1.0),
            TimingRecord("JSON", 10, 0.0),
        ]

        rows = build_timing_rows(records)

        self.assertEqual(rows[0][2], "1 секунда")
        self.assertEqual(rows[0][3], "—")
        self.assertEqual(rows[0][4], "—")
        self.assertEqual(rows[1][2], "0 секунд")
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

        self.assertEqual(rows[0][2], "1 second")
        self.assertEqual(rows[0][5], "Interrupted")
        self.assertEqual(rows[-1][0], "Folder total")
        self.assertEqual(rows[-1][5], "Interrupted")


if __name__ == "__main__":
    unittest.main()
