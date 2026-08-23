"""Regenerate documented artifacts from the public composition example."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from reactorcheck.io import load_config
from reactorcheck.plotting import save_result_plot
from reactorcheck.service import analyze_file

ROOT = Path(__file__).parents[1]
DATA = ROOT / "examples" / "synthetic_composition.csv"
CONFIG = ROOT / "examples" / "synthetic_composition_config.json"
ASSETS = ROOT / "docs" / "assets"


def main() -> None:
    """Create XLSX input, result plot, and a social-preview candidate."""
    frame = pd.read_csv(DATA)
    frame.to_excel(ROOT / "examples" / "synthetic_composition.xlsx", index=False)
    result = analyze_file(DATA, load_config(CONFIG))
    save_result_plot(result, ASSETS / "composition-result.png")

    summary = result.summary.set_index("metric")["value"]
    processed = result.processed
    figure, axis = plt.subplots(figsize=(12.8, 6.4), dpi=100, constrained_layout=True)
    axis.plot(
        processed["experiment_time_s"] / 60.0,
        100.0 * processed["conversion_CO_fraction"],
        color="#1769aa",
        linewidth=4,
        label="CO conversion",
    )
    axis.set_xlabel("Experiment time (min)", fontsize=15)
    axis.set_ylabel("CO conversion (%)", fontsize=15)
    axis.set_ylim(0, 60)
    axis.grid(alpha=0.2)
    axis.set_title(
        "ReactorCheck — auditable internal-standard reactor analysis",
        fontsize=22,
        loc="left",
        weight="bold",
    )
    text = (
        "N₂ standard: 1 mol h⁻¹\n"
        f"CO conversion: {summary['conversion_CO']:.3f}\n"
        f"CH₃OH C-selectivity: {summary['carbon_selectivity_CH3OH']:.3f}\n"
        f"C balance: {summary['element_balance_C']:.1f}%"
    )
    axis.text(
        0.98,
        0.12,
        text,
        transform=axis.transAxes,
        ha="right",
        va="bottom",
        fontsize=16,
        bbox={"boxstyle": "round,pad=0.7", "facecolor": "white", "alpha": 0.9},
    )
    axis.legend(loc="upper left", fontsize=14)
    figure.savefig(ASSETS / "social-preview.png", dpi=100)
    plt.close(figure)


if __name__ == "__main__":
    main()
