"""Quality-control checks, kept separate from scientific metric calculation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from reactorcheck.models import QCIssue


def _rows(mask: pd.Series | np.ndarray) -> tuple[int, ...]:
    values = np.flatnonzero(np.asarray(mask, dtype=bool))
    return tuple(int(value) for value in values[:100])


def input_issues(
    frame: pd.DataFrame, time_column: str, measured_columns: tuple[str, ...]
) -> list[QCIssue]:
    """Check missing data, duplicate times, negatives, and robust outliers."""
    issues: list[QCIssue] = []
    missing = frame.loc[:, [time_column, *measured_columns]].isna().any(axis="columns")
    if missing.any():
        issues.append(
            QCIssue(
                "missing_data",
                "error",
                "Required input data contain missing values",
                _rows(missing),
            )
        )
    duplicates = frame[time_column].duplicated(keep=False)
    if duplicates.any():
        issues.append(
            QCIssue(
                "duplicate_timestamps", "error", "Duplicate timestamps detected", _rows(duplicates)
            )
        )
    for column in measured_columns:
        negative = frame[column] < 0
        if negative.any():
            issues.append(
                QCIssue(
                    "negative_measurement",
                    "error",
                    f"Negative values in {column}",
                    _rows(np.asarray(negative, dtype=bool)),
                )
            )
        values = frame[column].to_numpy(dtype=float)
        median = float(np.nanmedian(values))
        mad = float(np.nanmedian(np.abs(values - median)))
        if mad > 0:
            robust_z = 0.67448975 * (values - median) / mad
            outliers = np.abs(robust_z) > 3.5
            if outliers.any():
                issues.append(
                    QCIssue(
                        "possible_outlier",
                        "warning",
                        f"Robust-MAD outlier in {column}",
                        _rows(outliers),
                    )
                )
    return issues


def metric_issues(
    processed: pd.DataFrame,
    product_names: tuple[str, ...],
    balance_tolerance_percent: float,
    physical_tolerance: float,
    steady_state_enabled: bool = True,
) -> list[QCIssue]:
    """Check physical ranges, selectivity closure, balances, and stability."""
    issues: list[QCIssue] = []
    columns = tuple(map(str, processed.columns))
    conversion_column = next((name for name in columns if name.startswith("conversion_")), None)
    if conversion_column:
        bad = (processed[conversion_column] < -physical_tolerance) | (
            processed[conversion_column] > 1 + physical_tolerance
        )
        if bad.any():
            issues.append(
                QCIssue(
                    "conversion_outside_physical_range",
                    "error",
                    "Conversion lies outside [0, 1]",
                    _rows(bad),
                )
            )
    selectivity_columns = [
        f"selectivity_carbon_{name}_fraction"
        for name in product_names
        if f"selectivity_carbon_{name}_fraction" in processed
    ]
    if selectivity_columns:
        total = processed[selectivity_columns].sum(axis=1, min_count=1)
        bad = total > 1 + physical_tolerance
        if bad.any():
            issues.append(
                QCIssue(
                    "selectivity_sum_exceeds_one",
                    "warning",
                    "Carbon selectivity sum exceeds unity",
                    _rows(bad),
                    float(total.max()),
                )
            )
    for element in ("C", "H", "O", "N"):
        column = f"element_balance_{element}_percent"
        if column in processed and processed[column].notna().any():
            deviation = (processed[column] - 100.0).abs()
            bad = deviation > balance_tolerance_percent
            if bad.any():
                code = "carbon_balance_deviation" if element == "C" else "element_balance_deviation"
                issues.append(
                    QCIssue(
                        code,
                        "warning",
                        f"{element} balance deviates by more than {balance_tolerance_percent:g}%",
                        _rows(bad),
                        float(deviation.max()),
                    )
                )
    if steady_state_enabled and "steady_state" in processed and not processed["steady_state"].all():
        issues.append(
            QCIssue(
                "non_steady_state_region",
                "info",
                "Some rows are outside detected/selected steady state",
                _rows(~processed["steady_state"]),
            )
        )
    return issues
