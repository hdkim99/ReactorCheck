"""Multi-variable steady-state detection with transparent rolling criteria."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray


@dataclass(frozen=True)
class SteadyStateResult:
    """Point-wise stable mask and contiguous candidate intervals."""

    mask: pd.Series
    intervals: tuple[tuple[float, float], ...]
    source: str


def _intervals(time: np.ndarray, mask: np.ndarray) -> tuple[tuple[float, float], ...]:
    result: list[tuple[float, float]] = []
    start: int | None = None
    for index, stable in enumerate(mask):
        if stable and start is None:
            start = index
        if start is not None and (not stable or index == len(mask) - 1):
            end = index if stable and index == len(mask) - 1 else index - 1
            result.append((float(time[start]), float(time[end])))
            start = None
    return tuple(result)


def detect_steady_state(
    frame: pd.DataFrame,
    time_column: str,
    variables: tuple[str, ...],
    minimum_window: int = 5,
    slope_tolerance: float = 0.02,
    variation_tolerance: float = 0.02,
    manual_range: tuple[float, float] | None = None,
) -> SteadyStateResult:
    """Find windows stable in every requested variable.

    For each trailing window and variable, two scale-normalized criteria apply:
    ``abs(linear_slope) * time_span / scale <= slope_tolerance`` and
    ``std / scale <= variation_tolerance``. ``scale`` is max(abs(mean), peak to
    peak, machine epsilon), preventing division by zero while remaining invariant
    to simple changes of units. A point is stable only when every variable passes.
    Manual override uses inclusive time bounds and bypasses automatic criteria.
    """
    if minimum_window < 3:
        raise ValueError("minimum_window must be at least 3")
    if not variables:
        mask = pd.Series(False, index=frame.index, dtype=bool)
        return SteadyStateResult(mask, (), "disabled")
    missing = [name for name in (time_column, *variables) if name not in frame]
    if missing:
        raise KeyError(f"Missing steady-state columns: {missing}")

    time = frame[time_column].to_numpy(dtype=float)
    if manual_range is not None:
        start, end = manual_range
        if end < start:
            raise ValueError("manual steady-state end precedes start")
        values = (time >= start) & (time <= end)
        mask = pd.Series(values, index=frame.index)
        return SteadyStateResult(mask, _intervals(time, values), "manual")

    stable: NDArray[np.bool_] = np.zeros(len(frame), dtype=bool)
    eps = float(np.finfo(float).eps)
    for end in range(minimum_window - 1, len(frame)):
        start = end - minimum_window + 1
        x = time[start : end + 1]
        if np.any(~np.isfinite(x)) or np.any(np.diff(x) <= 0):
            continue
        all_stable = True
        for variable in variables:
            y = frame[variable].to_numpy(dtype=float)[start : end + 1]
            if np.any(~np.isfinite(y)):
                all_stable = False
                break
            mean_magnitude = abs(float(np.mean(y)))
            peak_to_peak = float(np.ptp(y))
            scale = max(mean_magnitude, peak_to_peak, eps)
            slope = float(np.polyfit(x, y, deg=1)[0])
            normalized_drift = abs(slope) * float(x[-1] - x[0]) / scale
            normalized_variation = float(np.std(y, ddof=1)) / scale
            if normalized_drift > slope_tolerance or normalized_variation > variation_tolerance:
                all_stable = False
                break
        stable[end] = all_stable
    mask = pd.Series(stable, index=frame.index)
    return SteadyStateResult(mask, _intervals(time, stable), "automatic")
