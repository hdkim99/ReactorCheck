"""Tabular input, reproducible configuration, and multi-sheet export."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import pandas as pd

from reactorcheck.models import (
    AnalysisConfig,
    AnalysisResult,
    ChannelMapping,
    CompositionSettings,
    Species,
    SteadyStateSettings,
)
from reactorcheck.species import infer_species


class InputError(ValueError):
    """Raised for unsupported or invalid input data."""


_CSV_DELIMITERS = (",", ";", "\t")
_DERIVED_METRIC_TOKENS = {
    "CONVERSION",
    "ERROR",
    "SELECTIVITY",
    "UNCERTAINTY",
    "YIELD",
}


def _detect_csv_delimiter(source: Path) -> str:
    """Detect a conservative delimiter from structurally consistent rows.

    A candidate must split the header into multiple fields and produce the
    same number of fields in every sampled non-empty record. Multiple valid
    candidates are ambiguous and require the user to disambiguate the file.
    """
    try:
        with source.open(encoding="utf-8-sig", newline="") as stream:
            records = [line for line in stream if line.strip()][:50]
    except (OSError, UnicodeError) as exc:
        raise InputError(f"Could not inspect CSV delimiter: {exc}") from exc

    if not records:
        raise InputError("Input table is empty")

    candidates: list[str] = []
    observed: list[str] = []
    for delimiter in _CSV_DELIMITERS:
        try:
            rows = list(csv.reader(records, delimiter=delimiter, strict=True))
        except csv.Error:
            continue
        widths = [len(row) for row in rows]
        if widths[0] > 1:
            observed.append(delimiter)
        if widths[0] > 1 and len(set(widths)) == 1:
            candidates.append(delimiter)

    if len(candidates) > 1:
        names = {",": "comma", ";": "semicolon", "\t": "tab"}
        readable = ", ".join(names[value] for value in candidates)
        raise InputError(
            f"Ambiguous CSV delimiter: multiple consistent delimiters were found ({readable})"
        )
    if len(candidates) == 1:
        return candidates[0]
    if observed:
        names = {",": "comma", ";": "semicolon", "\t": "tab"}
        readable = ", ".join(names[value] for value in observed)
        raise InputError(
            "Could not determine a consistent CSV delimiter from the sampled rows "
            f"(header candidates: {readable})"
        )
    # Preserve valid one-column CSV behavior when the header has no candidate
    # delimiter. Comma is pandas' historical/default CSV basis.
    return ","


def _is_derived_metric_column(column: str) -> bool:
    """Return whether a header explicitly describes a derived/error metric."""
    if column.strip().lower().startswith("u_"):
        return True
    tokens = {token.upper() for token in re.findall(r"[A-Za-z0-9]+", column)}
    return bool(tokens & _DERIVED_METRIC_TOKENS)


def read_table(path: str | Path, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read CSV or XLSX without modifying source data."""
    source = Path(path)
    if not source.is_file():
        raise InputError(f"Input file does not exist: {source}")
    suffix = source.suffix.lower()
    if suffix == ".csv":
        delimiter = _detect_csv_delimiter(source)
        frame = pd.read_csv(source, sep=delimiter)
    elif suffix == ".xlsx":
        frame = pd.read_excel(source, sheet_name=sheet_name)
    else:
        raise InputError("Supported input formats are .csv and .xlsx")
    if frame.empty:
        raise InputError("Input table is empty")
    if len(set(map(str, frame.columns))) != len(frame.columns):
        raise InputError("Input columns must have unique names")
    return frame


def suggest_mappings(frame: pd.DataFrame) -> list[dict[str, str]]:
    """Conservatively suggest recognized species columns for user review."""
    suggestions: list[dict[str, str]] = []
    for column in frame.columns:
        if _is_derived_metric_column(str(column)):
            continue
        inferred = infer_species(str(column))
        if inferred is not None:
            name, formula = inferred
            suggestions.append({"column": str(column), "species": name, "formula": formula})
    return suggestions


def config_from_dict(raw: dict[str, Any]) -> AnalysisConfig:
    """Construct and validate config from JSON-compatible data."""
    try:
        channels = tuple(
            ChannelMapping(
                column=str(item["column"]),
                species=Species(str(item["species"]), str(item["formula"])),
                role=cast(Any, str(item["role"])),
                unit=str(item["unit"]),
                inlet=str(item["inlet"]) if item.get("inlet") is not None else None,
                inlet_column=str(item["inlet_column"])
                if item.get("inlet_column") is not None
                else None,
                inlet_unit=str(item["inlet_unit"]) if item.get("inlet_unit") is not None else None,
            )
            for item in raw["channels"]
        )
        steady_raw = raw.get("steady_state", {})
        steady = SteadyStateSettings(
            variables=tuple(str(value) for value in steady_raw.get("variables", [])),
            minimum_window=int(steady_raw.get("minimum_window", 5)),
            slope_tolerance=float(steady_raw.get("slope_tolerance", 0.02)),
            variation_tolerance=float(steady_raw.get("variation_tolerance", 0.02)),
            manual_start=float(steady_raw["manual_start"])
            if steady_raw.get("manual_start") is not None
            else None,
            manual_end=float(steady_raw["manual_end"])
            if steady_raw.get("manual_end") is not None
            else None,
        )
        composition_raw = raw.get("composition")
        composition = None
        if composition_raw is not None:
            if not isinstance(composition_raw, dict):
                raise ValueError("composition must be an object or null")
            if "basis" in composition_raw:
                raise ValueError(
                    "Ambiguous composition.basis is unsupported; set both "
                    "composition.normalization and composition.water_basis"
                )
            confirmed = composition_raw["confirmed_nonreactive"]
            if not isinstance(confirmed, bool):
                raise ValueError("confirmed_nonreactive must be a JSON boolean")
            composition = CompositionSettings(
                normalization=cast(Any, str(composition_raw["normalization"])),
                water_basis=cast(Any, str(composition_raw["water_basis"])),
                internal_standard=str(composition_raw["internal_standard"]),
                internal_standard_feed=str(composition_raw["internal_standard_feed"]),
                confirmed_nonreactive=confirmed,
                assumption=str(composition_raw["assumption"]),
                sum_tolerance_fraction=float(composition_raw.get("sum_tolerance_fraction", 0.02)),
            )
        return AnalysisConfig(
            time_column=str(raw["time_column"]),
            time_unit=str(raw["time_unit"]),
            channels=channels,
            reference_reactant=str(raw["reference_reactant"]),
            catalyst_mass=str(raw["catalyst_mass"]),
            standard_temperature=str(raw.get("standard_temperature", "273.15 K")),
            standard_pressure=str(raw.get("standard_pressure", "1 atm")),
            reactor_volume=str(raw["reactor_volume"])
            if raw.get("reactor_volume") is not None
            else None,
            volumetric_feed=str(raw["volumetric_feed"])
            if raw.get("volumetric_feed") is not None
            else None,
            mass_feed=str(raw["mass_feed"]) if raw.get("mass_feed") is not None else None,
            sty_product=str(raw["sty_product"]) if raw.get("sty_product") is not None else None,
            composition=composition,
            steady_state=steady,
            balance_tolerance_percent=float(raw.get("balance_tolerance_percent", 5.0)),
            physical_tolerance=float(raw.get("physical_tolerance", 1e-9)),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InputError(f"Invalid analysis configuration: {exc}") from exc


def config_to_dict(config: AnalysisConfig) -> dict[str, Any]:
    """Serialize config without derived Species fields."""
    return {
        "time_column": config.time_column,
        "time_unit": config.time_unit,
        "channels": [
            {
                "column": channel.column,
                "species": channel.species.name,
                "formula": channel.species.formula,
                "role": channel.role,
                "unit": channel.unit,
                "inlet": channel.inlet,
                "inlet_column": channel.inlet_column,
                "inlet_unit": channel.inlet_unit,
            }
            for channel in config.channels
        ],
        "reference_reactant": config.reference_reactant,
        "catalyst_mass": config.catalyst_mass,
        "standard_temperature": config.standard_temperature,
        "standard_pressure": config.standard_pressure,
        "reactor_volume": config.reactor_volume,
        "volumetric_feed": config.volumetric_feed,
        "mass_feed": config.mass_feed,
        "sty_product": config.sty_product,
        "composition": asdict(config.composition) if config.composition is not None else None,
        "steady_state": asdict(config.steady_state),
        "balance_tolerance_percent": config.balance_tolerance_percent,
        "physical_tolerance": config.physical_tolerance,
    }


def load_config(path: str | Path) -> AnalysisConfig:
    """Load a JSON analysis configuration."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"Could not read config: {exc}") from exc
    if not isinstance(raw, dict):
        raise InputError("Configuration root must be a JSON object")
    return config_from_dict(raw)


def save_config(config: AnalysisConfig, path: str | Path) -> None:
    """Save configuration in stable, human-readable JSON."""
    Path(path).write_text(json.dumps(config_to_dict(config), indent=2) + "\n", encoding="utf-8")


def export_excel(result: AnalysisResult, path: str | Path) -> None:
    """Export results, QC, settings, and provenance to a real XLSX workbook."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    settings_rows = [
        {"key": key, "value": json.dumps(value) if isinstance(value, (dict, list)) else value}
        for key, value in result.settings.items()
    ]
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        result.summary.to_excel(writer, sheet_name="summary", index=False)
        result.processed.to_excel(writer, sheet_name="processed", index=False)
        result.qc_frame().to_excel(writer, sheet_name="qc", index=False)
        pd.DataFrame(settings_rows).to_excel(writer, sheet_name="settings", index=False)
        result.provenance.to_excel(writer, sheet_name="provenance", index=False)


def export_csv_bundle(result: AnalysisResult, directory: str | Path) -> None:
    """Export every result component as a transparent CSV/JSON bundle."""
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    result.summary.to_csv(target / "summary.csv", index=False)
    result.processed.to_csv(target / "processed.csv", index=False)
    result.qc_frame().to_csv(target / "qc.csv", index=False)
    result.provenance.to_csv(target / "provenance.csv", index=False)
    (target / "settings.json").write_text(
        json.dumps(result.settings, indent=2) + "\n", encoding="utf-8"
    )
