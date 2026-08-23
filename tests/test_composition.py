from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from reactorcheck.composition import (
    CompositionError,
    reconstruct_with_internal_standard,
    to_fraction,
)
from reactorcheck.io import InputError, config_from_dict, load_config
from reactorcheck.models import (
    AnalysisConfig,
    ChannelMapping,
    CompositionSettings,
    Species,
)
from reactorcheck.service import AnalysisError, analyze_file, analyze_frame


def _channels(*, standard_role: str = "inert", water: bool = False) -> tuple[ChannelMapping, ...]:
    channels = [
        ChannelMapping("CO_pct", Species("CO", "CO"), "reactant", "percent", inlet="1 mol/h"),
        ChannelMapping("H2_pct", Species("H2", "H2"), "reactant", "percent", inlet="2 mol/h"),
        ChannelMapping("CH3OH_pct", Species("CH3OH", "CH3OH"), "product", "percent"),
        ChannelMapping("N2_pct", Species("N2", "N2"), standard_role, "percent"),
    ]
    if water:
        channels.append(ChannelMapping("H2O_pct", Species("H2O", "H2O"), "product", "percent"))
    return tuple(channels)


def _composition(
    *, normalization: str = "normalized", water_basis: str = "dry", feed: str = "1 mol/h"
) -> CompositionSettings:
    return CompositionSettings(
        normalization=normalization,
        water_basis=water_basis,
        internal_standard="N2",
        internal_standard_feed=feed,
        confirmed_nonreactive=True,
        assumption="N2 is deliberately nonreactive; F_N2,out = F_N2,in.",
        sum_tolerance_fraction=0.01,
    )


def _config(
    *,
    normalization: str = "normalized",
    water_basis: str = "dry",
    standard_role: str = "inert",
    water: bool = False,
    feed: str = "1 mol/h",
) -> AnalysisConfig:
    return AnalysisConfig(
        time_column="time_min",
        time_unit="min",
        channels=_channels(standard_role=standard_role, water=water),
        reference_reactant="CO",
        catalyst_mass="0.5 g",
        composition=_composition(normalization=normalization, water_basis=water_basis, feed=feed),
        sty_product="CH3OH",
    )


@pytest.mark.parametrize(
    ("unit", "value", "expected"),
    [
        ("fraction", 0.25, 0.25),
        ("percent", 25.0, 0.25),
        ("mol%", 25.0, 0.25),
        ("ppmv", 250_000, 0.25),
    ],
)
def test_composition_unit_conversion(unit: str, value: float, expected: float) -> None:
    assert to_fraction([value], unit)[0] == pytest.approx(expected)


def test_incompatible_composition_unit_fails() -> None:
    with pytest.raises(CompositionError, match="Unsupported composition unit"):
        to_fraction([1.0], "mol/h")


@pytest.mark.scientific
def test_internal_standard_hand_calculation_and_normalization_invariance() -> None:
    measurements = {"CO": [15.0], "CH3OH": [15.0], "N2": [30.0]}
    units = {name: "percent" for name in measurements}
    raw = reconstruct_with_internal_standard(measurements, units, "raw_measured", "N2", 1.0)
    normalized = reconstruct_with_internal_standard(measurements, units, "normalized", "N2", 1.0)
    assert raw.raw_sum[0] == pytest.approx(0.6)
    assert normalized.used_sum[0] == pytest.approx(1.0)
    assert not raw.normalization_applied
    assert normalized.normalization_applied
    for name, expected in {"CO": 0.5, "CH3OH": 0.5, "N2": 1.0}.items():
        assert raw.outlet_mol_h[name][0] == pytest.approx(expected)
        assert normalized.outlet_mol_h[name][0] == pytest.approx(expected)


@pytest.mark.parametrize("standard", [0.0, -0.1, np.nan])
def test_invalid_internal_standard_fraction_fails(standard: float) -> None:
    with pytest.raises(CompositionError, match="finite and positive"):
        reconstruct_with_internal_standard(
            {"CO": [0.2], "N2": [standard]},
            {"CO": "fraction", "N2": "fraction"},
            "normalized",
            "N2",
            1.0,
        )


def test_missing_internal_standard_channel_fails() -> None:
    with pytest.raises(CompositionError, match="missing"):
        reconstruct_with_internal_standard(
            {"CO": [0.2]}, {"CO": "fraction"}, "normalized", "N2", 1.0
        )


def test_negative_nonstandard_fraction_fails() -> None:
    with pytest.raises(CompositionError, match="Negative mole fractions"):
        reconstruct_with_internal_standard(
            {"CO": [-0.1], "N2": [0.5]},
            {"CO": "fraction", "N2": "fraction"},
            "raw_measured",
            "N2",
            1.0,
        )


@pytest.mark.scientific
@pytest.mark.integration
def test_composition_example_matches_hand_calculation() -> None:
    root = Path(__file__).parents[1]
    config = load_config(root / "examples" / "synthetic_composition_config.json")
    result = analyze_file(root / "examples" / "synthetic_composition.csv", config)
    frame = result.processed
    np.testing.assert_allclose(frame["flow_out_CO_mol_h"], 0.5, rtol=1e-9)
    np.testing.assert_allclose(frame["flow_out_H2_mol_h"], 1.0, rtol=1e-9)
    np.testing.assert_allclose(frame["flow_out_CH3OH_mol_h"], 0.5, rtol=1e-9)
    np.testing.assert_allclose(frame["flow_out_N2_mol_h"], 1.0, rtol=1e-9)
    np.testing.assert_allclose(frame["conversion_CO_fraction"], 0.5, rtol=1e-9)
    np.testing.assert_allclose(frame["selectivity_carbon_CH3OH_fraction"], 1.0, rtol=1e-9)
    np.testing.assert_allclose(frame["yield_molar_CH3OH_fraction"], 0.5, rtol=1e-9)
    np.testing.assert_allclose(frame["element_balance_C_percent"], 100.0, rtol=1e-9)
    np.testing.assert_allclose(frame["element_balance_H_percent"], 100.0, rtol=1e-9)
    np.testing.assert_allclose(frame["element_balance_O_percent"], 100.0, rtol=1e-9)
    assert result.settings["composition"]["water_basis"] == "dry"
    assert result.settings["composition"]["normalization"] == "normalized"
    provenance = result.provenance.iloc[0]
    assert provenance["workflow"] == "internal_standard"
    assert provenance["internal_standard"] == "N2"
    assert provenance["reference_reactant"] == "CO"
    assert provenance["normalization_applied"]
    assert "F_out_i" in provenance["reconstruction_method"]
    assert "nonreactive" in provenance["internal_standard_assumption"]


@pytest.mark.scientific
def test_raw_sum_qc_does_not_change_ratio_reconstruction() -> None:
    frame = pd.DataFrame(
        {
            "time_min": [0.0, 1.0, 2.0],
            "CO_pct": [15.0] * 3,
            "H2_pct": [30.0] * 3,
            "CH3OH_pct": [15.0] * 3,
            "N2_pct": [30.0] * 3,
        }
    )
    result = analyze_frame(frame, _config())
    assert "composition_sum_deviation" in {issue.code for issue in result.qc_issues}
    np.testing.assert_allclose(result.processed["flow_out_CO_mol_h"], 0.5)
    np.testing.assert_allclose(result.processed["composition_raw_sum_fraction"], 0.9)
    np.testing.assert_allclose(result.processed["composition_used_sum_fraction"], 1.0)


def test_reacting_or_unconfirmed_standard_is_rejected() -> None:
    with pytest.raises(ValueError, match="role 'inert'"):
        _config(standard_role="reactant")
    with pytest.raises(ValueError, match="explicit nonreactive confirmation"):
        replace(_composition(), confirmed_nonreactive=False)


def test_internal_standard_feed_unit_is_validated() -> None:
    frame = pd.DataFrame(
        {
            "time_min": [0.0],
            "CO_pct": [25.0],
            "H2_pct": [25.0],
            "CH3OH_pct": [25.0],
            "N2_pct": [25.0],
        }
    )
    with pytest.raises(AnalysisError, match="molar flow or standard volumetric flow"):
        analyze_frame(frame, _config(feed="1 kg"))


def test_wet_and_dry_are_independent_from_normalization() -> None:
    for normalization in ("raw_measured", "normalized"):
        assert _config(normalization=normalization, water_basis="dry").composition is not None
        assert (
            _config(normalization=normalization, water_basis="wet", water=True).composition
            is not None
        )


def test_water_basis_edge_cases_fail_explicitly() -> None:
    with pytest.raises(ValueError, match=r"Wet-basis.*H2O"):
        _config(water_basis="wet", water=False)
    with pytest.raises(ValueError, match=r"Dry-basis.*excludes H2O"):
        _config(water_basis="dry", water=True)


def test_ambiguous_single_basis_config_is_rejected() -> None:
    raw = {
        "time_column": "t",
        "time_unit": "s",
        "channels": [
            {
                "column": "co",
                "species": "CO",
                "formula": "CO",
                "role": "reactant",
                "unit": "percent",
                "inlet": "1 mol/h",
            },
            {"column": "n2", "species": "N2", "formula": "N2", "role": "inert", "unit": "percent"},
        ],
        "reference_reactant": "CO",
        "catalyst_mass": "1 g",
        "composition": {
            "basis": "normalized",
            "internal_standard": "N2",
            "internal_standard_feed": "1 mol/h",
            "confirmed_nonreactive": True,
            "assumption": "Explicit assumption",
        },
    }
    with pytest.raises(InputError, match=r"Ambiguous composition\.basis"):
        config_from_dict(raw)
