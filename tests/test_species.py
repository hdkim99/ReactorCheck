from __future__ import annotations

import pytest

from reactorcheck.models import Species
from reactorcheck.species import FormulaError, infer_species, parse_formula


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        ("CO2", {"C": 1, "O": 2}),
        ("CH3OH", {"C": 1, "H": 4, "O": 1}),
        ("C2H6", {"C": 2, "H": 6}),
        ("Ca(OH)2", {"Ca": 1, "O": 2, "H": 2}),
        ("Ar", {"Ar": 1}),
    ],
)
def test_formula_composition(formula: str, expected: dict[str, int]) -> None:
    assert parse_formula(formula) == expected


def test_species_derived_properties() -> None:
    species = Species("methanol", "CH3OH")
    assert species.carbon_number == 1
    assert species.molecular_weight_g_mol == pytest.approx(32.042)


@pytest.mark.parametrize("formula", ["", "Xx2", "Ca(OH2", "CO2+", "2H2"])
def test_invalid_formula_is_rejected(formula: str) -> None:
    with pytest.raises(FormulaError):
        parse_formula(formula)


def test_species_inference_requires_token() -> None:
    assert infer_species("outlet_CO2_mol_h") == ("CO2", "CO2")
    assert infer_species("SCORE") is None
