
"""Tests for gap-aware USGS water-stage segmentation."""

import pandas as pd
import pytest

from usgs_stage_peaks.segmentation import segment_stage_observations


def test_continuous_series():
    times = pd.date_range(
        "2025-07-01", periods=10, freq="5min", tz="UTC"
    )

    data = pd.DataFrame({
        "datetime": times,
        "Stage_ft": [8.0 + i * 0.1 for i in range(10)],
    })

    segmented, summary = segment_stage_observations(
        data,
        expected_interval_minutes=20,
    )

    assert len(segmented) == 10
    assert len(summary) == 1
    assert summary.iloc[0]["observations"] == 10


def test_isolated_peak_is_preserved():
    data = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-07-04T09:30:00Z",
            "2025-07-04T09:35:00Z",
            "2025-07-04T10:10:00Z",
            "2025-07-05T20:35:00Z",
            "2025-07-05T20:45:00Z",
            "2025-07-05T20:50:00Z",
        ]),
        "Stage_ft": [28.0, 29.45, 37.52, 8.89, 9.0, 9.1],
    })

    segmented, summary = segment_stage_observations(
        data,
        expected_interval_minutes=20,
    )

    # Under the 20-minute continuity rule:
    # Segment 1: 09:30, 09:35
    # Segment 2: 10:10 (isolated maximum)
    # Segment 3: 20:35, 20:45, 20:50
    assert len(segmented) == 6
    assert len(summary) == 3
    assert summary["observations"].tolist() == [2, 1, 3]

    peak = segmented.loc[segmented["Stage_ft"].idxmax()]

    assert peak["Stage_ft"] == pytest.approx(37.52)
    assert peak["segment_id"] == 2
    assert summary["observations"].sum() == len(data)

    peak = segmented.loc[segmented["Stage_ft"].idxmax()]

    assert peak["Stage_ft"] == pytest.approx(37.52)
    assert peak["segment_id"] == 2


def test_duplicate_timestamps_are_rejected():
    data = pd.DataFrame({
        "datetime": [
            "2025-07-04T09:30:00Z",
            "2025-07-04T09:30:00Z",
        ],
        "Stage_ft": [10.0, 11.0],
    })

    with pytest.raises(ValueError, match="Duplicate"):
        segment_stage_observations(data)


def test_invalid_stage_is_rejected():
    data = pd.DataFrame({
        "datetime": [
            "2025-07-04T09:30:00Z",
            "2025-07-04T09:35:00Z",
        ],
        "Stage_ft": [10.0, float("nan")],
    })

    with pytest.raises(ValueError, match="invalid"):
        segment_stage_observations(data)
def test_intervals_up_to_20_minutes_are_continuous():
    data = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-01T00:00:00Z",
            "2025-01-01T00:05:00Z",
            "2025-01-01T00:15:00Z",
            "2025-01-01T00:30:00Z",
            "2025-01-01T00:50:00Z",
            "2025-01-01T01:15:00Z",
        ]),
        "Stage_ft": [8, 9, 10, 11, 12, 13],
    })

    segmented, summary = segment_stage_observations(
        data,
        expected_interval_minutes=20,
    )

    assert len(summary) == 2
    assert summary["observations"].tolist() == [5, 1]