"""Real Tk widget-to-core integration smoke, executed under Xvfb in CI."""

from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path

from reactorcheck.gui import ReactorCheckApp
from reactorcheck.gui_controller import GUIController
from reactorcheck.io import load_config


def main(
    data_path: Path,
    config_path: Path,
    output_path: Path,
    conversion_column: str = "conversion_CO_fraction",
    expected_conversion: float = 0.5,
) -> None:
    """Exercise mapped controls, controller, service, core, and export."""
    root = tk.Tk()
    root.withdraw()
    controller = GUIController()
    controller.load(data_path)
    app = ReactorCheckApp(root, controller)
    app._apply_config(load_config(config_path))
    app.analyze()
    root.update()
    if controller.result is None:
        raise AssertionError("GUI Analyze did not produce a result")
    conversion = float(controller.result.processed[conversion_column].iloc[0])
    # Percent -> fraction -> internal-standard ratio involves ordinary binary
    # floating conversion. This matches the 1e-9 scientific regression tolerance.
    if abs(conversion - expected_conversion) > 1e-9:
        raise AssertionError(f"Unexpected GUI/core conversion: {conversion}")
    if not app.summary_tree.get_children():
        raise AssertionError("GUI result table was not populated")
    controller.export(output_path)
    if output_path.stat().st_size < 1000:
        raise AssertionError("GUI export was not written")
    root.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("data", type=Path)
    parser.add_argument("config", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--conversion-column", default="conversion_CO_fraction")
    parser.add_argument("--expected-conversion", type=float, default=0.5)
    arguments = parser.parse_args(sys.argv[1:])
    main(
        arguments.data,
        arguments.config,
        arguments.output,
        arguments.conversion_column,
        arguments.expected_conversion,
    )
