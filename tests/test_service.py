from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from reactorcheck.models import AnalysisConfig
from reactorcheck.service import AnalysisError, analyze_file, analyze_frame


@pytest.mark.integration
@pytest.mark.scientific
def test_example_service_matches_hand_calculation(
    example_csv, example_config: AnalysisConfig
) -> None:
    result = analyze_file(example_csv, example_config)
    frame = result.processed
    np.testing.assert_allclose(frame["conversion_CO_fraction"], 0.5)
    np.testing.assert_allclose(frame["selectivity_molar_CO2_fraction"], 1.0)
    np.testing.assert_allclose(frame["selectivity_carbon_CO2_fraction"], 1.0)
    np.testing.assert_allclose(frame["yield_molar_CO2_fraction"], 0.5)
    np.testing.assert_allclose(frame["rate_CO2_mol_gcat_h"], 1.0)
    np.testing.assert_allclose(frame["rate_CO2_mmol_gcat_h"], 1000.0)
    np.testing.assert_allclose(frame["rate_CO2_mol_kgcat_s"], 1000.0 / 3600.0)
    np.testing.assert_allclose(frame["element_balance_C_percent"], 100.0)
    np.testing.assert_allclose(frame["element_balance_H_percent"], 100.0)
    np.testing.assert_allclose(frame["element_balance_O_percent"], 100.0)
    np.testing.assert_allclose(frame["measured_mass_balance_percent"], 100.0)
    assert result.summary.set_index("metric").loc["GHSV", "value"] == pytest.approx(600.0)
    assert result.settings["steady_state_source"] == "automatic"
    assert len(result.provenance) == 4


def test_input_frame_is_not_mutated(example_csv, example_config: AnalysisConfig) -> None:
    original = pd.read_csv(example_csv)
    before = original.copy(deep=True)
    analyze_frame(original, example_config)
    pd.testing.assert_frame_equal(original, before)


def test_missing_mapped_column_fails(example_csv, example_config: AnalysisConfig) -> None:
    frame = pd.read_csv(example_csv).drop(columns=["CO_out"])
    with pytest.raises(AnalysisError, match="Mapped column not found"):
        analyze_frame(frame, example_config)


def test_negative_and_unphysical_values_produce_qc(
    example_csv, example_config: AnalysisConfig
) -> None:
    frame = pd.read_csv(example_csv)
    frame.loc[0, "CO_out"] = -0.1
    result = analyze_frame(frame, example_config)
    codes = {issue.code for issue in result.qc_issues}
    assert "negative_measurement" in codes
    assert "conversion_outside_physical_range" in codes


def test_duplicate_and_missing_data_produce_qc(example_csv, example_config: AnalysisConfig) -> None:
    frame = pd.read_csv(example_csv)
    frame.loc[1, "time_min"] = frame.loc[0, "time_min"]
    frame.loc[2, "CO_out"] = np.nan
    result = analyze_frame(frame, example_config)
    codes = {issue.code for issue in result.qc_issues}
    assert "duplicate_timestamps" in codes
    assert "missing_data" in codes
