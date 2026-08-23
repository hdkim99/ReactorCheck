from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from reactorcheck.steady import detect_steady_state


@pytest.mark.scientific
def test_multivariable_steady_state_rejects_drifting_channel() -> None:
    frame = pd.DataFrame(
        {
            "t": np.arange(20, dtype=float),
            "stable": np.ones(20),
            "drift": np.r_[np.linspace(0, 1, 10), np.ones(10)],
        }
    )
    result = detect_steady_state(frame, "t", ("stable", "drift"), 5, 0.02, 0.02)
    assert not result.mask.iloc[4]
    assert result.mask.iloc[-1]
    assert result.source == "automatic"


@pytest.mark.scientific
def test_sampling_density_does_not_change_constant_signal_classification() -> None:
    coarse = pd.DataFrame({"t": np.arange(10.0), "y": np.full(10, 5.0)})
    fine = pd.DataFrame({"t": np.arange(0.0, 10.0, 0.5), "y": np.full(20, 5.0)})
    coarse_result = detect_steady_state(coarse, "t", ("y",), 5)
    fine_result = detect_steady_state(fine, "t", ("y",), 5)
    assert coarse_result.mask.iloc[-1]
    assert fine_result.mask.iloc[-1]


@pytest.mark.scientific
def test_scale_change_preserves_classification() -> None:
    frame = pd.DataFrame({"t": np.arange(10.0), "y": np.linspace(10.0, 10.01, 10)})
    scaled = frame.assign(y=frame["y"] * 1000)
    assert detect_steady_state(frame, "t", ("y",), 5).mask.iloc[-1]
    assert detect_steady_state(scaled, "t", ("y",), 5).mask.iloc[-1]


@pytest.mark.scientific
def test_manual_override_is_inclusive_and_reported() -> None:
    frame = pd.DataFrame({"t": np.arange(6.0), "y": np.arange(6.0)})
    result = detect_steady_state(frame, "t", ("y",), manual_range=(2.0, 4.0))
    assert result.mask.tolist() == [False, False, True, True, True, False]
    assert result.intervals == ((2.0, 4.0),)
    assert result.source == "manual"
