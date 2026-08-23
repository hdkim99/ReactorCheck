from __future__ import annotations

import numpy as np
import pytest

from reactorcheck.units import UnitError, ensure_mass, to_molar_flow


def test_molar_flow_unit_conversion() -> None:
    actual = to_molar_flow([1000.0], "mmol/hour")
    np.testing.assert_allclose(actual, [1.0])


@pytest.mark.scientific
def test_sccm_uses_explicit_standard_state() -> None:
    # Ideal gas: 1 mol occupies 22.4139695 L at 273.15 K and 1 atm.
    actual = to_molar_flow([22413.9695], "sccm")
    assert actual[0] == pytest.approx(60.0, rel=2e-8)


def test_incompatible_flow_unit_fails_before_calculation() -> None:
    with pytest.raises(UnitError, match="molar flow or standard volumetric flow"):
        to_molar_flow([1.0], "kelvin")


def test_unknown_flow_unit_fails_before_calculation() -> None:
    with pytest.raises(UnitError, match="Invalid flow unit"):
        to_molar_flow([1.0], "definitely_not_a_unit")


def test_mass_dimension_validation() -> None:
    assert ensure_mass("0.5 kg") == pytest.approx(500.0)
    with pytest.raises(UnitError, match="Expected mass"):
        ensure_mass("5 mL")
