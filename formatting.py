"""Общие функции форматирования значений для интерфейса."""


def format_size(size: int) -> str:
    """Преобразовать размер в байтах в читаемую строку."""

    units = ("Б", "КБ", "МБ", "ГБ", "ТБ")
    value = float(size)

    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "Б":
                return "{} Б".format(int(value))
            if value >= 100:
                return "{:.0f} {}".format(value, unit)
            return "{:.1f} {}".format(value, unit).replace(".0 ", " ")
        value /= 1024

    return "{} Б".format(size)
