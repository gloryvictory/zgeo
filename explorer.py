"""Открытие выбранных файлов в системном файловом менеджере."""

from __future__ import annotations

import subprocess
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List


def group_files_by_folder(paths: Iterable[Path]) -> Dict[Path, List[Path]]:
    """Сгруппировать файлы по родительским каталогам, сохраняя порядок."""

    groups: "OrderedDict[Path, List[Path]]" = OrderedDict()
    for path in paths:
        path = Path(path)
        groups.setdefault(path.parent, []).append(path)
    return dict(groups)


def reveal_files(paths: Iterable[Path]) -> List[str]:
    """Открыть проводник с выбором файлов.

    Для каждой папки открывается отдельное окно. Если в папке выбрано
    несколько файлов, открывается первое из них — проводник Windows
    поддерживает выбор только одного элемента через командную строку.
    """

    errors: List[str] = []
    for _folder, files in group_files_by_folder(paths).items():
        try:
            _reveal_file(files[0])
        except OSError as error:
            errors.append("{}: {}".format(files[0], error))
    return errors


def _reveal_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        subprocess.Popen(
            ["explorer.exe", "/select,", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    elif sys.platform == "darwin":
        subprocess.Popen(
            ["open", "-R", str(path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        subprocess.Popen(
            ["xdg-open", str(path.parent)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
