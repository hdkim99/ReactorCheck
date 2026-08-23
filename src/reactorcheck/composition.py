"""Mole-fraction normalization and internal-standard flow reconstruction."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike, NDArray

from reactorcheck.models import CompositionTreatment


class CompositionError(ValueError):
    """Raised when a composition cannot be physically reconstructed."""


@dataclass(frozen=True)
class CompositionResolution:
    """Raw/used fractions and reconstructed outlet molar flows."""

    raw_fractions: dict[str, NDArray[np.float64]]
    used_fractions: dict[str, NDArray[np.float64]]
    outlet_mol_h: dict[str, NDArray[np.float64]]
    raw_sum: NDArray[np.float64]
    used_sum: NDArray[np.float64]
    normalization_applied: bool


def to_fraction(values: ArrayLike, unit: str) -> NDArray[np.float64]:
    """Convert an explicitly labeled composition unit to mole fraction."""
    normalized = unit.strip().lower().replace(" ", "_")
    factors = {
        "fraction": 1.0,
        "mole_fraction": 1.0,
        "mol/mol": 1.0,
        "1": 1.0,
        "%": 0.01,
        "percent": 0.01,
        "mol%": 0.01,
        "mole_percent": 0.01,
        "ppm": 1e-6,
        "ppmv": 1e-6,
    }
    if normalized not in factors:
        raise CompositionError(
            f"Unsupported composition unit {unit!r}; use fraction, percent/mol%, or ppm/ppmv"
        )
    return np.asarray(values, dtype=float) * factors[normalized]


def reconstruct_with_internal_standard(
    measurements: Mapping[str, ArrayLike],
    units: Mapping[str, str],
    normalization: CompositionTreatment,
    internal_standard: str,
    standard_feed_mol_h: float,
) -> CompositionResolution:
    """Reconstruct F_out,i = y_i/y_std * F_std,in.

    The caller must have already validated the user's explicit assumption that
    the standard is nonreactive, so F_std,out equals F_std,in. Normalization is
    applied only when ``normalization`` is ``normalized``. Wet/dry water basis is
    validated independently by the domain model and does not alter the ratio.
    Global normalization must not alter reconstructed flows; retaining raw and
    used values makes that invariant auditable.
    """
    if internal_standard not in measurements:
        raise CompositionError("Internal-standard composition channel is missing")
    if standard_feed_mol_h <= 0 or not np.isfinite(standard_feed_mol_h):
        raise CompositionError("Internal-standard feed flow must be finite and positive")
    raw = {name: to_fraction(values, units[name]) for name, values in measurements.items()}
    lengths = {len(values) for values in raw.values()}
    if len(lengths) != 1:
        raise CompositionError("Composition channels have inconsistent lengths")
    standard_values = raw[internal_standard]
    invalid_standard = ~np.isfinite(standard_values) | (standard_values <= 0)
    if invalid_standard.any():
        rows = tuple(int(value) for value in np.flatnonzero(invalid_standard)[:20])
        raise CompositionError(
            f"Internal-standard fraction must be finite and positive; invalid rows={rows}"
        )
    negative = {
        name: tuple(int(value) for value in np.flatnonzero(values < 0)[:20])
        for name, values in raw.items()
        if (values < 0).any()
    }
    if negative:
        raise CompositionError(f"Negative mole fractions are physically invalid: {negative}")

    stack = np.vstack(tuple(raw.values()))
    raw_sum = np.sum(stack, axis=0)
    normalization_applied = normalization == "normalized"
    if normalization_applied:
        invalid_sum = ~np.isfinite(raw_sum) | (raw_sum <= 0)
        if invalid_sum.any():
            rows = tuple(int(value) for value in np.flatnonzero(invalid_sum)[:20])
            raise CompositionError(
                "Composition sum must be finite and positive for normalization; "
                f"invalid rows={rows}"
            )
        used = {name: values / raw_sum for name, values in raw.items()}
    else:
        used = {name: values.copy() for name, values in raw.items()}
    used_sum = np.sum(np.vstack(tuple(used.values())), axis=0)
    used_standard = used[internal_standard]
    outlet = {name: (values / used_standard) * standard_feed_mol_h for name, values in used.items()}
    return CompositionResolution(
        raw_fractions=raw,
        used_fractions=used,
        outlet_mol_h=outlet,
        raw_sum=np.asarray(raw_sum, dtype=float),
        used_sum=np.asarray(used_sum, dtype=float),
        normalization_applied=normalization_applied,
    )
