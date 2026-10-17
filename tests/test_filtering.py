
"""Tests for the gap-aware recursive stage filter."""

import numpy as np
import pandas as pd
import pytest

from scipy.signal import lfilter

from usgs_stage_peaks.segmentation import (
    segment_stage_observations,
)
from usgs_stage_peaks.filtering import (
    lyne_hollick_baseline,
    filter_stage_segments,
)


def reference_filter(values, alpha=0.987):
    """Independent calculation matching the reference algorithm."""
    values = np.asarray(values, dtype=float)
    b = [(1 + alpha) / 2]
    a = [1, -alpha]

    forward = lfilter(
        b, a, np.diff(values, prepend=values[0])
    )
    backward = lfilter(
        b, a,
        np.diff(values[::-1], prepend=values[-1])
    )[::-1]

    return np.clip(
        values - (forward + backward) / 2,
        0,
        values,
    )


def test_filter_matches_reference():
    stage = np.array([
        8.0, 8.2, 9.1, 12.0, 10.5, 9.0, 8.1
    ])

    actual = lyne_hollick_baseline(stage)
    expected = reference_filter(stage)

    np.testing.assert_allclose(
        actual, expected, rtol=1e-12, atol=1e-12
    )


def test_filter_resets_at_gap():
    times = pd.to_datetime([
        "2025-07-04T09:20:00Z",
        "2025-07-04T09:25:00Z",
        "2025-07-04T09:30:00Z",
        "2025-07-04T09:35:00Z",
        "2025-07-05T20:45:00Z",
        "2025-07-05T20:50:00Z",
        "2025-07-05T20:55:00Z",
    ])

    data = pd.DataFrame({
        "datetime": times,
        "Stage_ft": [12, 18, 25, 29.45, 9, 9.2, 9.1],
    })

    segmented, summary = segment_stage_observations(data)
    filtered = filter_stage_segments(segmented)

    assert len(summary) == 2
    assert filtered["filter_applied"].all()

    for _, group in filtered.groupby("segment_id"):
        expected = reference_filter(
            group["Stage_ft"].to_numpy()
        )
        np.testing.assert_allclose(
            group["baseline_ft"].to_numpy(),
            expected,
        )


def test_isolated_peak_is_preserved():
    times = pd.to_datetime([
        "2025-07-04T09:25:00Z",
        "2025-07-04T09:30:00Z",
        "2025-07-04T09:35:00Z",
        "2025-07-04T10:10:00Z",
    ])

    data = pd.DataFrame({
        "datetime": times,
        "Stage_ft": [25.0, 27.0, 29.45, 37.52],
    })

    segmented, _ = segment_stage_observations(data)
    filtered = filter_stage_segments(segmented)

    peak = filtered.loc[filtered["Stage_ft"].idxmax()]

    assert peak["Stage_ft"] == pytest.approx(37.52)
    assert not peak["filter_applied"]
    assert pd.isna(peak["baseline_ft"])
    assert len(filtered) == 4


def test_invalid_alpha_rejected():
    with pytest.raises(ValueError):
        lyne_hollick_baseline(
            np.array([8.0, 9.0, 10.0]),
            alpha=1.5,
        )
