"""Учёт времени выполнения проверок и расчёт скорости обработки."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

from .i18n import LANGUAGE_EN, get_language, tr


@dataclass(frozen=True)
class TimingRecord:
    """Результат одной операции проверки."""

    operation: str
    files: int
    seconds: float
    completed: bool = True

    @property
    def files_per_second(self) -> Optional[float]:
        """Вернуть скорость обработки файлов в секунду."""

        if self.files <= 0 or self.seconds <= 0:
            return None
        return self.files / self.seconds

    @property
    def files_per_minute(self) -> Optional[float]:
        """Вернуть скорость обработки файлов в минуту."""

        speed = self.files_per_second
        return None if speed is None else speed * 60.0

    @property
    def status(self) -> str:
        """Вернуть локализованный статус операции."""

        return tr("Завершено") if self.completed else tr("Прервано")


def format_duration(seconds: float) -> str:
    """Вернуть длительность в человекочитаемом виде."""

    seconds = max(0.0, float(seconds))
    if 0.0 < seconds < 1.0:
        return tr("менее 1 секунды")

    total = int(seconds + 0.5)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []
    if hours:
        parts.append(
            _duration_part(
                hours,
                tr("час"),
                tr("часа"),
                tr("часов"),
            )
        )
    if minutes:
        parts.append(
            _duration_part(
                minutes,
                tr("минута"),
                tr("минуты"),
                tr("минут"),
            )
        )
    if secs or not parts:
        parts.append(
            _duration_part(
                secs,
                tr("секунда"),
                tr("секунды"),
                tr("секунд"),
            )
        )
    return " ".join(parts)


def _duration_part(
    value: int,
    one: str,
    few: str,
    many: str,
) -> str:
    if get_language() == LANGUAGE_EN:
        word = one if value == 1 else many
    else:
        word = _russian_plural(value, one, few, many)
    return f"{value} {word}"


def _russian_plural(value: int, one: str, few: str, many: str) -> str:
    value = abs(int(value))
    if value % 10 == 1 and value % 100 != 11:
        return one
    if 2 <= value % 10 <= 4 and not 12 <= value % 100 <= 14:
        return few
    return many


def build_timing_rows(
    records: Iterable[TimingRecord],
    *,
    total_files: Optional[int] = None,
    total_seconds: Optional[float] = None,
    completed: bool = True,
) -> List[List[object]]:
    """Построить строки листа с временем и скоростью проверок."""

    records = list(records)
    rows = [_record_row(record) for record in records]
    if (
        records
        and total_files is not None
        and total_seconds is not None
    ):
        rows.append(["", "", "", "", "", ""])
        rows.append(
            _record_row(
                TimingRecord(
                    tr("Итого по папке"),
                    total_files,
                    total_seconds,
                    completed,
                )
            )
        )
    return rows


def _record_row(record: TimingRecord) -> List[object]:
    files = max(0, int(record.files))
    seconds = max(0.0, float(record.seconds))
    return [
        record.operation,
        files,
        format_duration(seconds),
        _speed(files, seconds),
        _speed(files * 60.0, seconds),
        record.status,
    ]


def _speed(files: int, seconds: float) -> object:
    if files <= 0 or seconds <= 0:
        return "—"
    return round(files / seconds, 2)
