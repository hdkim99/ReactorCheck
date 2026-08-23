from __future__ import annotations

import re
from pathlib import Path

from reactorcheck import __version__

ROOT = Path(__file__).parents[1]


def _match(path: Path, pattern: str) -> str:
    matched = re.search(pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE)
    if matched is None:
        raise AssertionError(f"Version not found in {path}")
    return matched.group(1)


def test_version_surfaces_are_consistent() -> None:
    pyproject = _match(ROOT / "pyproject.toml", r'^version = "([^"]+)"$')
    citation = _match(ROOT / "CITATION.cff", r"^version: ([^\s]+)$")
    assert __version__ == pyproject == citation == "0.2.2"
