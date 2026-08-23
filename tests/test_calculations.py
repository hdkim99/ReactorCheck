from __future__ import annotations

import numpy as np
import pytest

from reactorcheck import calculations
from reactorcheck.models import Species


@pytest.mark.scientific
def test_hand_calculated_conversion_selectivity_yield() -> None:
    inlet = np.array([1.0])
    outlet = np.array([0.5])
    formed = np.array([0.5])
    consumed = inlet - outlet
    conversion = calculations.conversion(inlet, outlet)
    selectivity = calculations.molar_selectivity(formed, consumed)
    direct_yield = calculations.direct_yield(formed, inlet)
    np.testing.assert_allclose(conversion, [0.5])
    np.testing.assert_allclose(selectivity, [1.0])
    np.testing.assert_allclose(direct_yield, [0.5])
    np.testing.assert_allclose(direct_yield, conversion * selectivity)


@pytest.mark.scientific
def test_molar_and_carbon_selectivity_are_distinct() -> None:
    # 0.5 mol CO consumed, 0.25 mol C2H4 formed: S_molar=0.5; S_carbon=1.
    molar = calculations.molar_selectivity([0.25], [0.5])
    carbon = calculations.carbon_selectivity([0.25], 2, [0.5], 1)
    np.testing.assert_allclose(molar, [0.5])
    np.testing.assert_allclose(carbon, [1.0])


@pytest.mark.scientific
def test_exact_element_and_mass_recovery_for_water_gas_shift() -> None:
    species = {name: Species(name, name) for name in ("CO", "H2O", "CO2", "H2")}
    inlet = {
        "CO": np.array([1.0]),
        "H2O": np.array([1.0]),
        "CO2": np.array([0.0]),
        "H2": np.array([0.0]),
    }
    outlet = {
        "CO": np.array([0.5]),
        "H2O": np.array([0.5]),
        "CO2": np.array([0.5]),
        "H2": np.array([0.5]),
    }
    for element in ("C", "H", "O"):
        np.testing.assert_allclose(
            calculations.element_balance(inlet, outlet, species, element), [1.0]
        )
    np.testing.assert_allclose(calculations.mass_balance(inlet, outlet, species), [1.0])


def test_zero_feed_is_nan_not_false_success() -> None:
    assert np.isnan(calculations.conversion([0.0], [0.0])[0])


def test_rate_units_scale_and_invalid_mass() -> None:
    np.testing.assert_allclose(calculations.reaction_rate_mol_gcat_h([0.5], 0.5), [1.0])
    np.testing.assert_allclose(calculations.reaction_rate_mol_gcat_h([0.5], 1.0), [0.5])
    with pytest.raises(ValueError, match="positive"):
        calculations.reaction_rate_mol_gcat_h([0.5], 0.0)


def test_space_velocities() -> None:
    assert calculations.ghsv_h_inverse(6000, 10) == pytest.approx(600)
    assert calculations.whsv_h_inverse(5, 0.5) == pytest.approx(10)
