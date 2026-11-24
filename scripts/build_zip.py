"""Build the ZGeo plugin zip archive (cross-platform).

Mirrors ``scripts/build_zip.ps1`` so that CI and any OS can produce the
release artifact. The archive contains a top-level ``zgeo/`` folder with the
plugin files, excluding build/test/dev files.
"""

from __future__ import annotations

import configparser
import pathlib
import shutil
import sys
import tempfile
import zipfile

EXCLUDED_NAMES = {
    "__pycache__",
    "dist",
    "scripts",
    "tests",
    ".empryo",
    ".git",
    ".gitignore",
    ".github",
    ".ruff_cache",
    "ruff.toml",
    "AGENTS.md",
    "agents.md",
    ".idea",
    ".vscode",
}


def main() -> int:
    root = pathlib.Path(__file__).resolve().parent.parent
    metadata_path = root / "metadata.txt"
    if not metadata_path.exists():
        print("metadata.txt not found", file=sys.stderr)
        return 1

    config = configparser.ConfigParser()
    config.read(metadata_path, encoding="utf-8")
    version = config.get("general", "version", fallback="").strip()
    if not version:
        print("version is not defined in metadata.txt", file=sys.stderr)
        return 1

    plugin_name = root.name
    output_dir = root / "dist"
    output_dir.mkdir(exist_ok=True)
    zip_path = output_dir / "{}-{}.zip".format(plugin_name, version)

    staging = pathlib.Path(tempfile.mkdtemp(prefix="zgeo-build-"))
    staging_plugin = staging / plugin_name
    staging_plugin.mkdir(parents=True, exist_ok=True)

    try:
        for item in root.iterdir():
            if item.name in EXCLUDED_NAMES:
                continue
            target = staging_plugin / item.name
            if item.is_dir():
                shutil.copytree(
                    item,
                    target,
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
            else:
                shutil.copy2(item, target)

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(
            zip_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            for path in sorted(staging_plugin.rglob("*")):
                if path.is_dir():
                    continue
                relative = path.relative_to(staging_plugin).as_posix()
                archive.write(path, "{}/{}".format(plugin_name, relative))
    finally:
        shutil.rmtree(staging, ignore_errors=True)

    print("Created: {}".format(zip_path))
    print(
        "Install in QGIS: Plugins > Manage and Install Plugins > "
        "Install from ZIP"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
