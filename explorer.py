"""Открытие выбранных файлов в системном файловом менеджере."""

from __future__ import annotations

import os
import subprocess  # nosec B404
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List

_WINDOWS_EXPLORER = os.path.join(
    os.environ.get("SystemRoot", r"C:\Windows"), "explorer.exe"
)
_MACOS_OPEN = "/usr/bin/open"
_LINUX_OPEN = "/usr/bin/xdg-open"


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


def open_folder(path: Path) -> List[str]:
    """Открыть папку в системном файловом менеджере."""

    path = Path(path)
    try:
        _open_folder(path)
    except OSError as error:
        return ["{}: {}".format(path, error)]
    return []


def _launch(program: str, *arguments: str) -> None:
    """Запустить системную программу с фиксированным путём и без shell."""

    # The executable is fixed and the argument list is never passed to a shell.
    subprocess.Popen(  # nosec B603
        [program, *arguments],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _open_folder(path: Path) -> None:
    if sys.platform.startswith("win"):
        _launch(_WINDOWS_EXPLORER, str(path))
    elif sys.platform == "darwin":
        _launch(_MACOS_OPEN, str(path))
    else:
        _launch(_LINUX_OPEN, str(path))


def _reveal_file(path: Path) -> None:
    if sys.platform.startswith("win"):
        _launch(_WINDOWS_EXPLORER, "/select,", str(path))
    elif sys.platform == "darwin":
        _launch(_MACOS_OPEN, "-R", str(path))
    else:
        _launch(_LINUX_OPEN, str(path.parent))
