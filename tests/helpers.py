"""Shared helpers for the METAS_BELLO test suite."""

from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {
    ".cfg",
    ".env",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "env",
    "node_modules",
    "venv",
}


def read_project_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def iter_project_text_files() -> Iterable[Path]:
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        relative_parts = {part.lower() for part in path.relative_to(ROOT).parts}
        if relative_parts & EXCLUDED_DIRS:
            continue

        name = path.name.lower()
        if name.startswith(".env") or path.suffix.lower() in TEXT_SUFFIXES:
            yield path


def import_contract_module(module_path: str, skip_reason: str):
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as exc:
        missing = exc.name or ""
        if module_path == missing or module_path.startswith(f"{missing}."):
            raise unittest.SkipTest(skip_reason) from exc
        raise
