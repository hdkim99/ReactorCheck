"""Result plotting with a non-interactive-safe API."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from reactorcheck.models import AnalysisResult


def result_figure(result: AnalysisResult) -> Figure:
    """Plot conversion and product rates, shading selected steady-state points."""
    frame = result.processed
    columns = tuple(map(str, frame.columns))
    conversion_columns = [name for name in columns if name.startswith("conversion_")]
    rate_columns = [
        name
        for name in columns
        if name.startswith("rate_") and name.endswith("_mol_gcat_h") and "_mmol_" not in name
    ]
    figure, axes = plt.subplots(2, 1, sharex=True, figsize=(9, 6), constrained_layout=True)
    for column in conversion_columns:
        axes[0].plot(frame["experiment_time_s"], 100 * frame[column], label=column)
    axes[0].set_ylabel("Conversion (%)")
    axes[0].legend(loc="best")
    for column in rate_columns:
        axes[1].plot(frame["experiment_time_s"], frame[column], label=column)
    axes[1].set_ylabel("Rate (mol gcat$^{-1}$ h$^{-1}$)")
    axes[1].set_xlabel("Experiment time (s)")
    axes[1].legend(loc="best")
    if "steady_state" in frame:
        for axis in axes:
            axis.scatter(
                frame.loc[frame["steady_state"], "experiment_time_s"],
                [axis.get_ylim()[0]] * int(frame["steady_state"].sum()),
                marker="|",
                color="tab:green",
                alpha=0.5,
                label="steady-state",
            )
    return figure


def save_result_plot(result: AnalysisResult, path: str | Path, dpi: int = 160) -> None:
    """Save the standard analysis figure."""
    figure = result_figure(result)
    figure.savefig(path, dpi=dpi)
    plt.close(figure)
