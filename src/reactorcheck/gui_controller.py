"""Toolkit-independent application controller used by the desktop GUI."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from reactorcheck.io import export_excel, read_table
from reactorcheck.models import AnalysisConfig, AnalysisResult
from reactorcheck.plotting import save_result_plot
from reactorcheck.service import analyze_frame


class GUIController:
    """Stateful GUI/application boundary with no Tk dependency."""

    def __init__(self) -> None:
        self.data: pd.DataFrame | None = None
        self.source: Path | None = None
        self.result: AnalysisResult | None = None

    def load(self, path: str | Path) -> pd.DataFrame:
        """Load input through the public IO validator."""
        self.source = Path(path)
        self.data = read_table(path)
        self.result = None
        return self.data.copy(deep=True)

    def analyze(self, config: AnalysisConfig) -> AnalysisResult:
        """Execute the same service as the API and CLI."""
        if self.data is None:
            raise ValueError("Load a data file first")
        self.result = analyze_frame(
            self.data,
            config,
            source=str(self.source.resolve()) if self.source else "GUI in-memory",
        )
        return self.result

    def export(self, path: str | Path) -> None:
        """Export the complete current result."""
        if self.result is None:
            raise ValueError("Run an analysis before export")
        export_excel(self.result, path)

    def save_plot(self, path: str | Path) -> None:
        """Export a plot derived from the current real result."""
        if self.result is None:
            raise ValueError("Run an analysis before plotting")
        save_result_plot(self.result, path)
