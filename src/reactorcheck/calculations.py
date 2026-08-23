"""Pure scientific calculations for catalytic reactor data.

All flow arrays accepted here are mol/h. Dimensioned inputs are normalized by
the service layer before entering this module, keeping equations explicit and
testable without any GUI or file-I/O state.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
from numpy.typing import ArrayLike, NDArray

from reactorcheck.models import Species


def _arrays(
    numerator: ArrayLike, denominator: ArrayLike
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    return np.asarray(numerator, dtype=float), np.asarray(denominator, dtype=float)


def safe_ratio(numerator: ArrayLike, denominator: ArrayLike) -> NDArray[np.float64]:
    """Divide while representing a zero/invalid denominator as NaN."""
    top, bottom = _arrays(numerator, denominator)
    result = np.full(np.broadcast_shapes(top.shape, bottom.shape), np.nan, dtype=float)
    valid = np.isfinite(top) & np.isfinite(bottom) & (bottom != 0.0)
    np.divide(top, bottom, out=result, where=valid)
    return result


def conversion(inlet: ArrayLike, outlet: ArrayLike) -> NDArray[np.float64]:
    """Reactant conversion X = (F_in - F_out) / F_in."""
    inlet_array, outlet_array = _arrays(inlet, outlet)
    return safe_ratio(inlet_array - outlet_array, inlet_array)


def net_formation(inlet: ArrayLike, outlet: ArrayLike) -> NDArray[np.float64]:
    """Net species formation F_out - F_in in mol/h."""
    inlet_array, outlet_array = _arrays(inlet, outlet)
    return outlet_array - inlet_array


def molar_selectivity(
    product_formation: ArrayLike, reactant_consumption: ArrayLike
) -> NDArray[np.float64]:
    """Molar selectivity = mol product formed / mol reference reactant consumed."""
    return safe_ratio(product_formation, reactant_consumption)


def carbon_selectivity(
    product_formation: ArrayLike,
    product_carbon_number: int,
    reactant_consumption: ArrayLike,
    reactant_carbon_number: int,
) -> NDArray[np.float64]:
    """Carbon selectivity based on carbon atoms in net product and consumed feed."""
    if reactant_carbon_number <= 0:
        return np.full(np.asarray(product_formation).shape, np.nan, dtype=float)
    return safe_ratio(
        np.asarray(product_formation) * product_carbon_number,
        np.asarray(reactant_consumption) * reactant_carbon_number,
    )


def direct_yield(product_formation: ArrayLike, reactant_inlet: ArrayLike) -> NDArray[np.float64]:
    """Molar product yield = net mol product formed / mol reference reactant fed.

    Under the same molar basis, this is identically conversion times molar
    selectivity. Keeping the direct equation permits an independent consistency
    check in the service and tests.
    """
    return safe_ratio(product_formation, reactant_inlet)


def element_balance(
    inlet_flows: Mapping[str, NDArray[np.float64]],
    outlet_flows: Mapping[str, NDArray[np.float64]],
    species: Mapping[str, Species],
    element: str,
) -> NDArray[np.float64]:
    """Element recovery = total elemental molar outflow / inflow."""
    sample = next(iter(outlet_flows.values()))
    element_in = np.zeros_like(sample, dtype=float)
    element_out = np.zeros_like(sample, dtype=float)
    for name, item in species.items():
        count = item.composition.get(element, 0)
        element_in += inlet_flows[name] * count
        element_out += outlet_flows[name] * count
    return safe_ratio(element_out, element_in)


def mass_balance(
    inlet_flows: Mapping[str, NDArray[np.float64]],
    outlet_flows: Mapping[str, NDArray[np.float64]],
    species: Mapping[str, Species],
) -> NDArray[np.float64]:
    """Measured-species mass recovery = Σ(F_out MW) / Σ(F_in MW).

    This is a measured-stream closure, not a total plant balance when unmeasured
    species exist; the report labels it accordingly.
    """
    sample = next(iter(outlet_flows.values()))
    mass_in = np.zeros_like(sample, dtype=float)
    mass_out = np.zeros_like(sample, dtype=float)
    for name, item in species.items():
        mass_in += inlet_flows[name] * item.molecular_weight_g_mol
        mass_out += outlet_flows[name] * item.molecular_weight_g_mol
    return safe_ratio(mass_out, mass_in)


def reaction_rate_mol_gcat_h(
    formation_mol_h: ArrayLike, catalyst_mass_g: float
) -> NDArray[np.float64]:
    """Net formation rate r = ΔF / m_cat in mol g_cat⁻¹ h⁻¹."""
    if catalyst_mass_g <= 0:
        raise ValueError("Catalyst mass must be positive")
    return np.asarray(formation_mol_h, dtype=float) / catalyst_mass_g


def sty_gproduct_gcat_h(
    formation_mol_h: ArrayLike,
    molecular_weight_g_mol: float,
    catalyst_mass_g: float,
) -> NDArray[np.float64]:
    """Mass-based STY = ΔF_product MW_product / m_cat."""
    return reaction_rate_mol_gcat_h(formation_mol_h, catalyst_mass_g) * molecular_weight_g_mol


def ghsv_h_inverse(volumetric_feed_ml_h: float, reactor_volume_ml: float) -> float:
    """GHSV = standard volumetric feed rate / packed reactor volume, h⁻¹."""
    if volumetric_feed_ml_h < 0 or reactor_volume_ml <= 0:
        raise ValueError("Feed flow cannot be negative and reactor volume must be positive")
    return volumetric_feed_ml_h / reactor_volume_ml


def whsv_h_inverse(mass_feed_g_h: float, catalyst_mass_g: float) -> float:
    """WHSV = total feed mass flow / catalyst mass, h⁻¹."""
    if mass_feed_g_h < 0 or catalyst_mass_g <= 0:
        raise ValueError("Feed flow cannot be negative and catalyst mass must be positive")
    return mass_feed_g_h / catalyst_mass_g
