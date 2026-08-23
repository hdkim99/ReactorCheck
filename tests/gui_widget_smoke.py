"""Real Tk widget-to-core integration smoke, executed under Xvfb in CI."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

from reactorcheck.gui import ReactorCheckApp
from reactorcheck.gui_controller import GUIController
from reactorcheck.io import load_config


def main(data_path: Path, config_path: Path, output_path: Path) -> None:
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
    conversion = float(controller.result.processed["conversion_CO_fraction"].iloc[0])
    if abs(conversion - 0.5) > 1e-12:
        raise AssertionError(f"Unexpected GUI/core conversion: {conversion}")
    if not app.summary_tree.get_children():
        raise AssertionError("GUI result table was not populated")
    controller.export(output_path)
    if output_path.stat().st_size < 1000:
        raise AssertionError("GUI export was not written")
    root.destroy()


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
