"""Minimal regressions derived from public laboratory data.

RC-PUB-001
    Source DOI: 10.5281/zenodo.8314734
    Source files: A1_G1_FBTesting_XDB4x_RawData.xlsx and
    A1_G1_FBData_XDB4x_mean.csv
    License: CC BY 4.0
    Reduction: retain public column names for mapping and one measured row for
    ratio reconstruction, with explicit attribution in the test docstring; no
    source file is redistributed.

RC-PUB-002
    Source DOI: 10.17632/sw7225g8xr.3
    Source file: data_V2.csv, zero-based data rows 0 and 1
    License: CC BY 4.0
    Reduction: retain the public header and two representative, unmodified
    records needed to reproduce delimiter detection; no source file is
    redistributed.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from reactorcheck.io import InputError, read_table, suggest_mappings
from reactorcheck.models import (
    AnalysisConfig,
    ChannelMapping,
    CompositionSettings,
    Species,
)
from reactorcheck.service import analyze_frame

RWGS_HEADER = (
    "H2toCO2;GHSV;pset;Tout;Tset;GA_H2_corrected;GA_CH4_corrected;"
    "GA_CO_corrected;GA_CO2_corrected;u_GA_H2;u_GA_CH4;u_GA_CO;"
    "u_GA_CO2;XCO2;SCO"
)
RWGS_ROWS = (
    "3.00;8000.00;1.00;576.11;550.00;63.76;10.36;9.66;20.29;"
    "1.6E+00;1.2E-01;2.6E-01;3.1E-01;52.86;48.11",
    "3.00;8000.00;3.00;579.84;550.00;58.81;16.02;7.69;21.79;"
    "1.6E+00;2.3E-01;2.0E-01;3.4E-01;54.82;31.88",
)


def test_public_semicolon_csv_is_read_as_fifteen_columns(tmp_path: Path) -> None:
    source = tmp_path / "data_V2.csv"
    source.write_text("\r\n".join((RWGS_HEADER, *RWGS_ROWS)) + "\r\n", encoding="ascii")

    frame = read_table(source)

    assert frame.shape == (2, 15)
    assert list(frame.columns[-3:]) == ["u_GA_CO2", "XCO2", "SCO"]
    assert frame.loc[0, "GA_CO2_corrected"] == pytest.approx(20.29)


def test_ambiguous_csv_delimiter_fails_explicitly(tmp_path: Path) -> None:
    source = tmp_path / "ambiguous.csv"
    source.write_text("a,b;c\n1,2;3\n", encoding="utf-8")

    with pytest.raises(InputError, match="Ambiguous CSV delimiter"):
        read_table(source)


def test_structurally_inconsistent_public_delimiter_fails_explicitly(tmp_path: Path) -> None:
    source = tmp_path / "ragged.csv"
    source.write_text("a;b\n1;2;3\n", encoding="utf-8")

    with pytest.raises(InputError, match="consistent CSV delimiter"):
        read_table(source)


def test_public_metric_and_uncertainty_columns_are_not_species_measurements() -> None:
    columns = [
        "GA_CO_corrected",
        "GA_CO2_corrected",
        "u_GA_CO",
        "u_GA_CO2",
        "CO2 Conversion (%)",
        "MeOH Selectivity (%)",
        "CH4 Selectivity(%)",
        "CO Selectivity(%)",
        "CO2_fr (ml/min)",
    ]

    suggestions = suggest_mappings(read_table_from_header(columns))

    assert suggestions == [
        {"column": "GA_CO_corrected", "species": "CO", "formula": "CO"},
        {"column": "GA_CO2_corrected", "species": "CO2", "formula": "CO2"},
        {"column": "CO2_fr (ml/min)", "species": "CO2", "formula": "CO2"},
    ]


def test_public_raw_gc_header_recognizes_helium_without_selecting_a_detector() -> None:
    columns = [
        "FID_B_CO2_Conc",
        "TCD_Aux_CO2_Conc",
        "TCD_Aux_H2_Conc",
        "TCD_Aux_He_Conc",
        "TCD_Aux_N2_Conc",
    ]

    suggestions = suggest_mappings(read_table_from_header(columns))

    assert {item["column"] for item in suggestions} == set(columns)
    assert next(item for item in suggestions if item["column"] == "TCD_Aux_He_Conc") == {
        "column": "TCD_Aux_He_Conc",
        "species": "He",
        "formula": "He",
    }
    assert sum(item["species"] == "CO2" for item in suggestions) == 2
    assert Species("He", "He").molecular_weight_g_mol == pytest.approx(4.002602)


@pytest.mark.scientific
def test_public_raw_gc_row_supports_explicit_helium_reconstruction() -> None:
    """RC-PUB-001: one measured row exercises explicit He reconstruction.

    Derived from DOI 10.5281/zenodo.8314734, file
    A1_G1_FBTesting_XDB4x_RawData.xlsx, sheet ``Run Data``, identified by
    ``SampleTimeId=715``, ``Reactor=1``, and ``ElapsedRunTime=4.423007``
    (CC BY 4.0). The single row retains only analysis values and is not a substitute
    for validating the full source workbook. Feed ratios follow the cited
    publication; the explicit nonreactive He assumption remains user-owned.
    """
    frame = pd.DataFrame(
        {
            "ElapsedRunTime": [4.423007],
            "TCD_Aux_CO2_Conc": [8.955452],
            "TCD_Aux_H2_Conc": [25.381241],
            "TCD_Aux_He_Conc": [6.170010],
            "TCD_Aux_N2_Conc": [56.361374],
            "TCD_Aux_CO_Conc": [0.0],
            "FID_F_CH4_Conc": [0.111773],
            "FID_B_MeOH_Conc": [0.0],
        }
    )
    channels = (
        ChannelMapping(
            "TCD_Aux_CO2_Conc", Species("CO2", "CO2"), "reactant", "percent", "1.875 mL/min"
        ),
        ChannelMapping(
            "TCD_Aux_H2_Conc", Species("H2", "H2"), "reactant", "percent", "5.625 mL/min"
        ),
        ChannelMapping("TCD_Aux_He_Conc", Species("He", "He"), "inert", "percent"),
        ChannelMapping("TCD_Aux_N2_Conc", Species("N2", "N2"), "inert", "percent", "3.5 mL/min"),
        ChannelMapping("TCD_Aux_CO_Conc", Species("CO", "CO"), "product", "percent"),
        ChannelMapping("FID_F_CH4_Conc", Species("CH4", "CH4"), "product", "percent"),
        ChannelMapping("FID_B_MeOH_Conc", Species("CH3OH", "CH3OH"), "product", "percent"),
    )
    config = AnalysisConfig(
        time_column="ElapsedRunTime",
        time_unit="h",
        channels=channels,
        reference_reactant="CO2",
        catalyst_mass="0.05 g",
        composition=CompositionSettings(
            normalization="raw_measured",
            water_basis="dry",
            internal_standard="He",
            internal_standard_feed="1.5 mL/min",
            confirmed_nonreactive=True,
            assumption=(
                "The user confirms the publication's deliberately added He is "
                "nonreactive, so F_He,out = F_He,in."
            ),
        ),
    )

    result = analyze_frame(frame, config, source="RC-PUB-001 minimal measured row")

    processed = result.processed.iloc[0]
    assert processed["flow_out_CO2_mol_h"] / processed["flow_out_He_mol_h"] == pytest.approx(
        8.955452 / 6.170010
    )
    assert processed["flow_out_H2_mol_h"] / processed["flow_out_He_mol_h"] == pytest.approx(
        25.381241 / 6.170010
    )
    provenance = result.provenance.iloc[0]
    assert provenance["internal_standard"] == "He"
    assert provenance["internal_standard_assumption"] == config.composition.assumption


def read_table_from_header(columns: list[str]) -> pd.DataFrame:
    """Build an in-memory table without introducing a bundled data fixture."""
    return pd.DataFrame(columns=columns, index=[0], dtype=float)
