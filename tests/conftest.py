from __future__ import annotations

from pathlib import Path

import pytest

from reactorcheck.io import load_config
from reactorcheck.models import AnalysisConfig

ROOT = Path(__file__).parents[1]


@pytest.fixture
def example_csv() -> Path:
    return ROOT / "examples" / "synthetic_reactor.csv"


@pytest.fixture
def example_config() -> AnalysisConfig:
    return load_config(ROOT / "examples" / "synthetic_config.json")
