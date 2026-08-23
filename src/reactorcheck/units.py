"""Unit handling and standard-state gas-flow conversions.

Volumetric gas flows are converted using the ideal-gas equation at an explicit
standard temperature and pressure. No ambient-condition assumption is hidden.
"""

from __future__ import annotations

from typing import Any, TypeAlias

import numpy as np
import pint
from numpy.typing import ArrayLike, NDArray

ureg: pint.UnitRegistry[Any] = pint.UnitRegistry(autoconvert_offset_to_baseunit=True)
ureg.define("sccm = centimeter ** 3 / minute")
Q_: TypeAlias = pint.Quantity[Any]

STANDARD_TEMPERATURE = 273.15 * ureg.kelvin
STANDARD_PRESSURE = 1.0 * ureg.atmosphere
GAS_CONSTANT = 8.31446261815324 * ureg.joule / ureg.mole / ureg.kelvin


class UnitError(ValueError):
    """Raised when a quantity has an incompatible physical dimension."""


def quantity(text: str) -> Q_:
    """Parse a required value-with-unit string."""
    try:
        result: Q_ = ureg.Quantity(text)
    except (pint.PintError, TypeError) as exc:
        raise UnitError(f"Invalid quantity {text!r}: {exc}") from exc
    if result.dimensionless:
        raise UnitError(f"A physical unit is required for {text!r}")
    return result


def to_molar_flow(
    values: ArrayLike,
    unit: str,
    standard_temperature: Q_ = STANDARD_TEMPERATURE,
    standard_pressure: Q_ = STANDARD_PRESSURE,
) -> NDArray[np.float64]:
    """Convert molar or standard volumetric gas flow values to mol/h."""
    array = np.asarray(values, dtype=float)
    try:
        source = array * ureg(unit)
    except pint.PintError as exc:
        raise UnitError(f"Invalid flow unit {unit!r}: {exc}") from exc
    try:
        return np.asarray(source.to("mol/hour").magnitude, dtype=float)
    except pint.DimensionalityError:
        try:
            volume_flow = source.to("meter**3/second")
            molar = (
                standard_pressure.to("pascal")
                * volume_flow
                / (GAS_CONSTANT * standard_temperature.to("kelvin"))
            )
            return np.asarray(molar.to("mol/hour").magnitude, dtype=float)
        except pint.DimensionalityError as exc:
            raise UnitError(
                f"Flow unit {unit!r} must be molar flow or standard volumetric flow"
            ) from exc


def ensure_mass(text: str, target: str = "g") -> float:
    """Return a mass quantity in ``target`` units."""
    try:
        return float(quantity(text).to(target).magnitude)
    except pint.DimensionalityError as exc:
        raise UnitError(f"Expected mass, got {text!r}") from exc


def ensure_volume(text: str, target: str = "mL") -> float:
    """Return a volume quantity in ``target`` units."""
    try:
        return float(quantity(text).to(target).magnitude)
    except pint.DimensionalityError as exc:
        raise UnitError(f"Expected volume, got {text!r}") from exc


def ensure_mass_flow(text: str, target: str = "g/hour") -> float:
    """Return a mass-flow quantity in ``target`` units."""
    try:
        return float(quantity(text).to(target).magnitude)
    except pint.DimensionalityError as exc:
        raise UnitError(f"Expected mass flow, got {text!r}") from exc
