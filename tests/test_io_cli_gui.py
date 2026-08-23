from __future__ import annotations

import json
from pathlib import Path

import openpyxl
import pandas as pd
import pytest

from reactorcheck.cli import main
from reactorcheck.gui_controller import GUIController
from reactorcheck.io import export_csv_bundle, export_excel, read_table
from reactorcheck.models import AnalysisConfig
from reactorcheck.service import analyze_file


def test_csv_and_xlsx_input(tmp_path: Path, example_csv: Path) -> None:
    expected = read_table(example_csv)
    xlsx = tmp_path / "input.xlsx"
    expected.to_excel(xlsx, index=False)
    pd.testing.assert_frame_equal(read_table(xlsx), expected, check_dtype=False)


@pytest.mark.integration
def test_excel_export_contains_complete_sections(
    tmp_path: Path, example_csv: Path, example_config: AnalysisConfig
) -> None:
    result = analyze_file(example_csv, example_config)
    output = tmp_path / "result.xlsx"
    export_excel(result, output)
    workbook = openpyxl.load_workbook(output, read_only=True)
    assert workbook.sheetnames == ["summary", "processed", "qc", "settings", "provenance"]
    settings = pd.read_excel(output, sheet_name="settings").set_index("key")
    assert "steady_state" in settings.index
    provenance = pd.read_excel(output, sheet_name="provenance")
    assert set(("source_file", "source_column", "source_unit")) <= set(provenance.columns)


def test_csv_bundle_includes_settings(
    tmp_path: Path, example_csv: Path, example_config: AnalysisConfig
) -> None:
    export_csv_bundle(analyze_file(example_csv, example_config), tmp_path / "bundle")
    settings = json.loads((tmp_path / "bundle" / "settings.json").read_text())
    assert settings["reference_reactant"] == "CO"


@pytest.mark.integration
def test_cli_smoke(tmp_path: Path, example_csv: Path) -> None:
    config = example_csv.parent / "synthetic_config.json"
    output = tmp_path / "cli.xlsx"
    plot = tmp_path / "plot.png"
    assert (
        main(
            ["analyze", str(example_csv), "-c", str(config), "-o", str(output), "--plot", str(plot)]
        )
        == 0
    )
    assert output.stat().st_size > 1000
    assert plot.stat().st_size > 1000


def test_cli_rejects_missing_config(tmp_path: Path, example_csv: Path, capsys) -> None:
    code = main(
        [
            "analyze",
            str(example_csv),
            "-c",
            str(tmp_path / "missing.json"),
            "-o",
            str(tmp_path / "x.xlsx"),
        ]
    )
    assert code == 2
    assert "error" in capsys.readouterr().err


@pytest.mark.gui
@pytest.mark.integration
def test_gui_controller_calls_real_service_and_export(
    tmp_path: Path, example_csv: Path, example_config: AnalysisConfig
) -> None:
    controller = GUIController()
    controller.load(example_csv)
    result = controller.analyze(example_config)
    assert result.processed["conversion_CO_fraction"].iloc[0] == pytest.approx(0.5)
    output = tmp_path / "gui.xlsx"
    controller.export(output)
    assert "settings" in openpyxl.load_workbook(output, read_only=True).sheetnames
    plot = tmp_path / "gui.png"
    controller.save_plot(plot)
    assert plot.stat().st_size > 1000
