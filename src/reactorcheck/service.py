"""Application service connecting IO, units, scientific core, QC, and exports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
import pint
from numpy.typing import NDArray

from reactorcheck import calculations
from reactorcheck.io import config_to_dict, read_table
from reactorcheck.models import AnalysisConfig, AnalysisResult, QCIssue
from reactorcheck.qc import input_issues, metric_issues
from reactorcheck.steady import detect_steady_state
from reactorcheck.units import (
    Q_,
    UnitError,
    ensure_mass,
    ensure_mass_flow,
    ensure_volume,
    quantity,
    to_molar_flow,
    ureg,
)


class AnalysisError(ValueError):
    """Raised when data/configuration cannot produce a valid analysis."""


def _require_numeric(frame: pd.DataFrame, columns: set[str]) -> None:
    for column in columns:
        if column not in frame:
            raise AnalysisError(f"Mapped column not found: {column}")
        try:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        except (ValueError, TypeError) as exc:
            raise AnalysisError(f"Column {column!r} must be numeric") from exc


def _time_seconds(values: pd.Series, unit: str) -> np.ndarray:
    try:
        converted = np.asarray(
            (values.to_numpy(dtype=float) * ureg(unit)).to("second").magnitude, dtype=float
        )
        return cast(NDArray[np.float64], converted)
    except pint.PintError as exc:
        raise AnalysisError(f"Time unit {unit!r} is not a time dimension") from exc


def _standard_state(config: AnalysisConfig) -> tuple[Q_, Q_]:
    temperature = quantity(config.standard_temperature)
    pressure = quantity(config.standard_pressure)
    try:
        return temperature.to("kelvin"), pressure.to("pascal")
    except pint.DimensionalityError as exc:
        raise AnalysisError("Standard temperature/pressure have incompatible units") from exc


def _flow_arrays(
    frame: pd.DataFrame, config: AnalysisConfig
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    temperature, pressure = _standard_state(config)
    inlet: dict[str, np.ndarray] = {}
    outlet: dict[str, np.ndarray] = {}
    for channel in config.channels:
        try:
            outlet[channel.species.name] = to_molar_flow(
                frame[channel.column].to_numpy(),
                channel.unit,
                standard_temperature=temperature,
                standard_pressure=pressure,
            )
            if channel.inlet_column is not None and channel.inlet_unit is not None:
                inlet[channel.species.name] = to_molar_flow(
                    frame[channel.inlet_column].to_numpy(),
                    channel.inlet_unit,
                    standard_temperature=temperature,
                    standard_pressure=pressure,
                )
            elif channel.inlet is not None:
                parsed = quantity(channel.inlet)
                scalar = to_molar_flow(
                    [parsed.magnitude],
                    str(parsed.units),
                    standard_temperature=temperature,
                    standard_pressure=pressure,
                )[0]
                inlet[channel.species.name] = np.full(len(frame), scalar)
            elif channel.role == "reactant":
                raise AnalysisError(
                    f"Reactant {channel.species.name} requires inlet or inlet_column"
                )
            else:
                inlet[channel.species.name] = np.zeros(len(frame))
        except UnitError as exc:
            raise AnalysisError(str(exc)) from exc
    return inlet, outlet


def _add_summary(
    rows: list[dict[str, Any]],
    metric: str,
    values: pd.Series | np.ndarray,
    unit: str,
    mask: pd.Series,
) -> None:
    series = pd.Series(values)
    selected = series[mask.to_numpy()] if mask.any() else series
    finite = selected[np.isfinite(selected)]
    rows.append(
        {
            "metric": metric,
            "value": float(finite.mean()) if len(finite) else np.nan,
            "unit": unit,
            "n": len(finite),
            "scope": "steady_state" if mask.any() else "all_rows",
        }
    )


def analyze_frame(
    data: pd.DataFrame,
    config: AnalysisConfig,
    *,
    source: str = "in-memory",
) -> AnalysisResult:
    """Analyze one reactor table through the same path used by CLI and GUI."""
    if data.empty:
        raise AnalysisError("Input data are empty")
    frame = data.copy(deep=True)
    required = {config.time_column}
    for channel in config.channels:
        required.add(channel.column)
        if channel.inlet_column is not None:
            required.add(channel.inlet_column)
    _require_numeric(frame, required)
    measured = tuple(channel.column for channel in config.channels)
    issues = input_issues(frame, config.time_column, measured)

    processed = frame.copy(deep=True)
    processed["experiment_time_s"] = _time_seconds(frame[config.time_column], config.time_unit)
    inlet, outlet = _flow_arrays(frame, config)
    species = {channel.species.name: channel.species for channel in config.channels}
    roles = {channel.species.name: channel.role for channel in config.channels}
    for name in species:
        processed[f"flow_in_{name}_mol_h"] = inlet[name]
        processed[f"flow_out_{name}_mol_h"] = outlet[name]
        processed[f"net_formation_{name}_mol_h"] = calculations.net_formation(
            inlet[name], outlet[name]
        )

    reference = config.reference_reactant
    reference_consumption = inlet[reference] - outlet[reference]
    conversion = calculations.conversion(inlet[reference], outlet[reference])
    processed[f"conversion_{reference}_fraction"] = conversion
    product_names = tuple(name for name, role in roles.items() if role == "product")
    catalyst_mass_g = ensure_mass(config.catalyst_mass)
    for name in product_names:
        formation = outlet[name] - inlet[name]
        molar = calculations.molar_selectivity(formation, reference_consumption)
        carbon = calculations.carbon_selectivity(
            formation,
            species[name].carbon_number,
            reference_consumption,
            species[reference].carbon_number,
        )
        direct = calculations.direct_yield(formation, inlet[reference])
        processed[f"selectivity_molar_{name}_fraction"] = molar
        processed[f"selectivity_carbon_{name}_fraction"] = carbon
        processed[f"yield_molar_{name}_fraction"] = direct
        processed[f"yield_consistency_error_{name}"] = direct - conversion * molar
        rate_base = calculations.reaction_rate_mol_gcat_h(formation, catalyst_mass_g)
        processed[f"rate_{name}_mol_gcat_h"] = rate_base
        processed[f"rate_{name}_mmol_gcat_h"] = 1000.0 * rate_base
        processed[f"rate_{name}_mol_kgcat_s"] = (1000.0 / 3600.0) * rate_base

    elements = sorted({element for item in species.values() for element in item.composition})
    for element in elements:
        processed[f"element_balance_{element}_percent"] = 100.0 * calculations.element_balance(
            inlet, outlet, species, element
        )
    processed["measured_mass_balance_percent"] = 100.0 * calculations.mass_balance(
        inlet, outlet, species
    )

    if config.sty_product is not None:
        if config.sty_product not in product_names:
            raise AnalysisError("sty_product must name a mapped product")
        product = species[config.sty_product]
        processed[f"sty_{product.name}_gproduct_gcat_h"] = calculations.sty_gproduct_gcat_h(
            outlet[product.name] - inlet[product.name],
            product.molecular_weight_g_mol,
            catalyst_mass_g,
        )

    settings = config.steady_state
    manual: tuple[float, float] | None = None
    if settings.manual_start is not None or settings.manual_end is not None:
        if settings.manual_start is None or settings.manual_end is None:
            raise AnalysisError("Both manual_start and manual_end are required")
        time_factor = float((1 * ureg(config.time_unit)).to("second").magnitude)
        manual = (settings.manual_start * time_factor, settings.manual_end * time_factor)
    steady = detect_steady_state(
        processed,
        "experiment_time_s",
        settings.variables,
        settings.minimum_window,
        settings.slope_tolerance,
        settings.variation_tolerance,
        manual,
    )
    processed["steady_state"] = steady.mask
    issues.extend(
        metric_issues(
            processed,
            product_names,
            config.balance_tolerance_percent,
            config.physical_tolerance,
            steady.source != "disabled",
        )
    )
    max_consistency = max(
        (float(processed[f"yield_consistency_error_{name}"].abs().max()) for name in product_names),
        default=0.0,
    )
    if max_consistency > max(config.physical_tolerance, 1e-12):
        issues.append(
            QCIssue(
                "yield_definition_inconsistency",
                "error",
                "Direct yield differs from conversion times selectivity",
                value=max_consistency,
            )
        )

    summary_rows: list[dict[str, Any]] = []
    _add_summary(summary_rows, f"conversion_{reference}", conversion, "fraction", steady.mask)
    for name in product_names:
        _add_summary(
            summary_rows,
            f"molar_selectivity_{name}",
            processed[f"selectivity_molar_{name}_fraction"],
            "fraction",
            steady.mask,
        )
        _add_summary(
            summary_rows,
            f"carbon_selectivity_{name}",
            processed[f"selectivity_carbon_{name}_fraction"],
            "fraction",
            steady.mask,
        )
        _add_summary(
            summary_rows,
            f"molar_yield_{name}",
            processed[f"yield_molar_{name}_fraction"],
            "fraction",
            steady.mask,
        )
        _add_summary(
            summary_rows,
            f"reaction_rate_{name}",
            processed[f"rate_{name}_mol_gcat_h"],
            "mol gcat^-1 h^-1",
            steady.mask,
        )
    for element in elements:
        _add_summary(
            summary_rows,
            f"element_balance_{element}",
            processed[f"element_balance_{element}_percent"],
            "%",
            steady.mask,
        )
    _add_summary(
        summary_rows,
        "measured_mass_balance",
        processed["measured_mass_balance_percent"],
        "%",
        steady.mask,
    )
    if config.sty_product is not None:
        column = f"sty_{config.sty_product}_gproduct_gcat_h"
        _add_summary(
            summary_rows,
            f"STY_{config.sty_product}",
            processed[column],
            "gproduct gcat^-1 h^-1",
            steady.mask,
        )
    if config.volumetric_feed is not None or config.reactor_volume is not None:
        if config.volumetric_feed is None or config.reactor_volume is None:
            raise AnalysisError("GHSV requires both volumetric_feed and reactor_volume")
        try:
            flow = float(quantity(config.volumetric_feed).to("mL/hour").magnitude)
            volume = ensure_volume(config.reactor_volume)
        except (UnitError, pint.DimensionalityError) as exc:
            raise AnalysisError("GHSV requires volume/time feed and reactor volume") from exc
        summary_rows.append(
            {
                "metric": "GHSV",
                "value": calculations.ghsv_h_inverse(flow, volume),
                "unit": "h^-1",
                "n": 1,
                "scope": "configuration",
            }
        )
    if config.mass_feed is not None:
        mass_feed = ensure_mass_flow(config.mass_feed)
        summary_rows.append(
            {
                "metric": "WHSV",
                "value": calculations.whsv_h_inverse(mass_feed, catalyst_mass_g),
                "unit": "h^-1",
                "n": 1,
                "scope": "configuration",
            }
        )

    provenance = pd.DataFrame(
        [
            {
                "output_prefix": channel.species.name,
                "source_file": source,
                "source_column": channel.column,
                "source_unit": channel.unit,
                "species_formula": channel.species.formula,
                "inlet_source": channel.inlet_column
                or channel.inlet
                or "zero (product/inert default)",
                "standard_temperature": config.standard_temperature,
                "standard_pressure": config.standard_pressure,
            }
            for channel in config.channels
        ]
    )
    settings_export = config_to_dict(config)
    settings_export["steady_state_source"] = steady.source
    settings_export["steady_state_intervals_s"] = [list(interval) for interval in steady.intervals]
    return AnalysisResult(
        processed, pd.DataFrame(summary_rows), issues, settings_export, provenance
    )


def analyze_file(path: str | Path, config: AnalysisConfig) -> AnalysisResult:
    """Read and analyze a CSV/XLSX file."""
    return analyze_frame(read_table(path), config, source=str(Path(path).resolve()))
