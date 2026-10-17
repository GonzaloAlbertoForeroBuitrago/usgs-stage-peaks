
"""Unit tests for stage-event detection."""

import numpy as np
import pandas as pd

from usgs_stage_peaks.events import detect_stage_events


def make_filtered(stage, baseline):
    n = len(stage)

    return pd.DataFrame({
        "datetime": pd.date_range(
            "2025-01-01",
            periods=n,
            freq="5min",
            tz="UTC",
        ),
        "Stage_ft": stage,
        "baseline_ft": baseline,
        "segment_id": 1,
        "filter_applied": True,
    })


def test_detects_one_event():
    data = make_filtered(
        stage=[8, 8, 10, 15, 10, 8, 8],
        baseline=[8, 8, 8, 8, 8, 8, 8],
    )

    events = detect_stage_events(data)

    assert len(events) == 1
    assert events.iloc[0]["flow_peak"] == 15
    assert events.iloc[0]["i_peak"] == 3


def test_no_events():
    data = make_filtered(
        stage=[8, 8, 8, 8, 8],
        baseline=[8, 8, 8, 8, 8],
    )

    events = detect_stage_events(data)

    assert events.empty


def test_preserves_original_volume_columns():
    data = make_filtered(
        stage=[8, 8, 10, 15, 10, 8, 8],
        baseline=[8, 8, 8, 8, 8, 8, 8],
    )

    events = detect_stage_events(data)

    assert "event_volume" in events.columns
    assert "baseflow_volume" in events.columns

    assert np.isfinite(events.iloc[0]["event_volume"])
    assert np.isfinite(events.iloc[0]["baseflow_volume"])


def test_skips_unfiltered_isolated_segment():
    data = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-07-04T10:10:00Z",
        ]),
        "Stage_ft": [37.52],
        "baseline_ft": [np.nan],
        "segment_id": [2],
        "filter_applied": [False],
    })

    events = detect_stage_events(data)

    assert events.empty

    # The observation remains available for peaks.py.
    assert data.iloc[0]["Stage_ft"] == 37.52
