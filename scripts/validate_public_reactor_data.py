"""Opt-in validation against checksum-pinned public reactor datasets.

The script never downloads or rewrites source data. Download the three files
from the cited repositories, pass their local paths, and use a new/empty output
directory. See ``docs/public-data-sources.md`` for sources, licenses, and the
scientific limits of each comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import openpyxl
import pandas as pd

from reactorcheck.cli import main as cli_main
from reactorcheck.gui_controller import GUIController
from reactorcheck.io import read_table, save_config, suggest_mappings
from reactorcheck.models import AnalysisConfig, ChannelMapping, Species
from reactorcheck.service import analyze_frame

EXPECTED_FILES = {
    "swisscat_raw": {
        "name": "A1_G1_FBTesting_XDB4x_RawData.xlsx",
        "size": 150_533,
        "sha256": "85726cbefbbaf808b2a2936b418f28bcb646d0c7e00cd4690a679f81c2f65d83",
        "doi": "10.5281/zenodo.8314734",
    },
    "swisscat_mean": {
        "name": "A1_G1_FBData_XDB4x_mean.csv",
        "size": 8_032,
        "sha256": "92a93f9174b66a22faae53f92c6f996d595567cf056a0c2a7c8872e3a4d0a217",
        "doi": "10.5281/zenodo.8314734",
    },
    "rwgs": {
        "name": "data_V2.csv",
        "size": 31_698,
        "sha256": "9700726a1146c812b8dbb63ab5d7e8cf4fcf55e480668a52fbe0287bac3077b2",
        "doi": "10.17632/sw7225g8xr.3",
    },
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_source(path: Path, key: str) -> dict[str, Any]:
    expected = EXPECTED_FILES[key]
    if not path.is_file():
        raise ValueError(f"Missing source file: {path}")
    actual_size = path.stat().st_size
    actual_sha256 = _sha256(path)
    if path.name != expected["name"]:
        raise ValueError(f"Expected {expected['name']!r}, received {path.name!r}")
    if actual_size != expected["size"] or actual_sha256 != expected["sha256"]:
        raise ValueError(
            f"Checksum/size mismatch for {path.name}; do not validate a changed source file"
        )
    return {
        "path": str(path.resolve()),
        "size": actual_size,
        "sha256": actual_sha256,
        "doi": expected["doi"],
    }


def _mean_config() -> AnalysisConfig:
    """Map the selected Swiss Cat+ processed flow columns without redefining them."""
    channels = (
        ChannelMapping(
            "CO2_fr (ml/min)",
            Species("CO2", "CO2"),
            "reactant",
            "mL/min",
            inlet_column="CO2_in (ml/min)",
            inlet_unit="mL/min",
        ),
        ChannelMapping(
            "H2_fr (ml/min)",
            Species("H2", "H2"),
            "reactant",
            "mL/min",
            inlet_column="H2_in (ml/min)",
            inlet_unit="mL/min",
        ),
        ChannelMapping(
            "He_fr (ml/min)",
            Species("He", "He"),
            "inert",
            "mL/min",
            inlet_column="He_in (ml/min)",
            inlet_unit="mL/min",
        ),
        ChannelMapping(
            "N2_fr (ml/min)",
            Species("N2", "N2"),
            "inert",
            "mL/min",
            inlet_column="N2_in (ml/min)",
            inlet_unit="mL/min",
        ),
        ChannelMapping("CO_fr (ml/min)", Species("CO", "CO"), "product", "mL/min"),
        ChannelMapping("CH4_fr (ml/min)", Species("CH4", "CH4"), "product", "mL/min"),
        ChannelMapping("MeOH_fr (ml/min)", Species("MeOH", "CH3OH"), "product", "mL/min"),
    )
    return AnalysisConfig(
        time_column="Time on Stream (h)",
        time_unit="h",
        channels=channels,
        reference_reactant="CO2",
        catalyst_mass="50 mg",
        sty_product="MeOH",
    )


def _prepare_output(path: Path) -> None:
    if path.exists() and any(path.iterdir()):
        raise ValueError(f"Output directory must be new or empty: {path}")
    path.mkdir(parents=True, exist_ok=True)


def validate(args: argparse.Namespace) -> dict[str, Any]:
    """Run read-only source checks and real API/CLI/GUI-controller paths."""
    output = args.output_dir.resolve()
    _prepare_output(output)
    sources = {
        "swisscat_raw": _verify_source(args.swisscat_raw, "swisscat_raw"),
        "swisscat_mean": _verify_source(args.swisscat_mean, "swisscat_mean"),
        "rwgs": _verify_source(args.rwgs, "rwgs"),
    }

    raw = read_table(args.swisscat_raw, sheet_name="Run Data")
    mean = read_table(args.swisscat_mean)
    rwgs = read_table(args.rwgs)
    if raw.shape != (125, 175) or mean.shape != (16, 39) or rwgs.shape != (313, 15):
        raise AssertionError(
            f"Unexpected source shapes: raw={raw.shape}, mean={mean.shape}, rwgs={rwgs.shape}"
        )

    raw_suggestions = suggest_mappings(raw)
    mean_suggestions = suggest_mappings(mean)
    rwgs_suggestions = suggest_mappings(rwgs)
    if not any(item["species"] == "He" for item in raw_suggestions):
        raise AssertionError("Helium was not suggested from the public raw GC header")
    if sum(item["species"] == "CO2" for item in raw_suggestions) < 2:
        raise AssertionError(
            "Detector-specific duplicate CO2 channels were not preserved for review"
        )
    excluded_headers = {
        "CO2 Conversion (%)",
        "MeOH Selectivity (%)",
        "CH4 Selectivity(%)",
        "CO Selectivity(%)",
        "u_GA_CO",
        "u_GA_CO2",
    }
    mapped_headers = {item["column"] for item in (*mean_suggestions, *rwgs_suggestions)}
    if mapped_headers & excluded_headers:
        raise AssertionError("Derived metrics or uncertainty columns were mapped as measurements")

    config = _mean_config()
    api_result = analyze_frame(mean, config, source=str(args.swisscat_mean.resolve()))
    if "conversion_outside_physical_range" not in {issue.code for issue in api_result.qc_issues}:
        raise AssertionError("Expected the published-definition mismatch to remain visible in QC")

    config_path = output / "swisscat-mean-config.json"
    cli_output = output / "swisscat-mean-cli.xlsx"
    cli_raw_suggestions = output / "swisscat-raw-suggestions.json"
    cli_mean_suggestions = output / "swisscat-mean-suggestions.json"
    save_config(config, config_path)
    if cli_main(["suggest", str(args.swisscat_raw), "--output", str(cli_raw_suggestions)]):
        raise AssertionError("CLI raw mapping suggestion failed")
    if cli_main(["suggest", str(args.swisscat_mean), "--output", str(cli_mean_suggestions)]):
        raise AssertionError("CLI processed mapping suggestion failed")
    if cli_main(
        [
            "analyze",
            str(args.swisscat_mean),
            "--config",
            str(config_path),
            "--output",
            str(cli_output),
        ]
    ):
        raise AssertionError("CLI real-data analysis/export failed")

    controller = GUIController()
    controller.load(args.swisscat_raw)
    if controller.data is None or controller.data.shape != raw.shape:
        raise AssertionError("GUI controller did not load the raw workbook losslessly")
    controller.load(args.swisscat_mean)
    gui_result = controller.analyze(config)
    gui_output = output / "swisscat-mean-gui-controller.xlsx"
    controller.export(gui_output)

    cli_processed = pd.read_excel(cli_output, sheet_name="processed")
    np.testing.assert_allclose(
        api_result.processed["conversion_CO2_fraction"],
        cli_processed["conversion_CO2_fraction"],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        api_result.processed["conversion_CO2_fraction"],
        gui_result.processed["conversion_CO2_fraction"],
        rtol=1e-12,
        atol=1e-12,
    )
    expected_sheets = {"summary", "processed", "qc", "settings", "provenance"}
    for workbook_path in (cli_output, gui_output):
        sheets = set(openpyxl.load_workbook(workbook_path, read_only=True).sheetnames)
        if sheets != expected_sheets:
            raise AssertionError(f"Incomplete export workbook: {workbook_path}")

    computed = 100.0 * api_result.processed["conversion_CO2_fraction"].to_numpy()
    published = mean["CO2 Conversion (%)"].to_numpy(dtype=float)
    report = {
        "sources": sources,
        "source_shapes": {
            "swisscat_raw": list(raw.shape),
            "swisscat_mean": list(mean.shape),
            "rwgs": list(rwgs.shape),
        },
        "validation_level": {
            "swisscat_raw": "raw-workbook IO and conservative mapping only",
            "swisscat_mean": "processed-flow API/CLI/GUI-controller/export path",
            "rwgs": "processed dry-composition CSV delimiter and mapping only",
        },
        "transformations": [],
        "excluded_rows": [],
        "scientific_definition_difference": {
            "reactorcheck": "direct inlet/outlet CO2 disappearance",
            "publication": "carbon-normalized CO2 conversion",
            "maximum_absolute_percentage_point_difference": float(
                np.max(np.abs(computed - published))
            ),
            "comparison_status": "unsupported definition difference; not reconciled",
        },
        "qc_codes": sorted({issue.code for issue in api_result.qc_issues}),
        "outputs": [
            str(config_path),
            str(cli_raw_suggestions),
            str(cli_mean_suggestions),
            str(cli_output),
            str(gui_output),
        ],
    }
    report_path = output / "validation-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    """Build the opt-in validation CLI."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--swisscat-raw", required=True, type=Path)
    parser.add_argument("--swisscat-mean", required=True, type=Path)
    parser.add_argument("--rwgs", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main() -> None:
    """Validate selected public files supplied explicitly by the user."""
    report = validate(build_parser().parse_args())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
