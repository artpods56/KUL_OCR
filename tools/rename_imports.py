#!/usr/bin/env python3
"""One-off import renamer for monorepo transition.

Replaces the old `kul_ocr` package name with new `core` and updates
entrypoint imports to `backend.entrypoints`.

Run from repository root:
    python scripts/rename_imports.py
"""

from __future__ import annotations

from pathlib import Path

# Directories to process
TARGET_DIRS = [
    Path("lib/core"),
    Path("services/backend"),
    Path("tests"),
]

# Ordered replacements (specific first)
REPLACEMENTS = [
    ("kul_ocr.entrypoints", "backend.entrypoints"),
    ("kul_ocr", "core"),
]


def should_edit(path: Path) -> bool:
    if path.suffix != ".py":
        return False
    parts = set(path.parts)
    if "__pycache__" in parts or ".egg-info" in parts:
        return False
    return True


def rewrite_file(path: Path) -> bool:
    text = path.read_text()
    new_text = text
    for old, new in REPLACEMENTS:
        new_text = new_text.replace(old, new)
    if new_text != text:
        path.write_text(new_text)
        return True
    return False


def main() -> None:
    changed = 0
    for base in TARGET_DIRS:
        for file_path in base.rglob("*.py"):
            if not should_edit(file_path):
                continue
            if rewrite_file(file_path):
                changed += 1
                print(f"rewrote {file_path}")
    print(f"done, changed {changed} files")


if __name__ == "__main__":
    main()
