
"""Validate the default 60-minute continuity rule."""

import pandas as pd

from usgs_stage_peaks import segment_stage_observations


def test_default_60_minute_continuity():

    observations = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-01T00:00:00Z",
            "2025-01-01T00:15:00Z",
            "2025-01-01T00:45:00Z",
            "2025-01-01T01:45:00Z",
            "2025-01-01T03:00:00Z",
        ]),
        "Stage_ft": [
            8.0, 8.2, 8.5, 9.0, 8.3,
        ],
    })

    segmented, summary = segment_stage_observations(
        observations
    )

    assert len(segmented) == 5
    assert len(summary) == 2

    assert summary["observations"].tolist() == [4, 1]

    assert segmented["segment_id"].tolist() == [
        1, 1, 1, 1, 2
    ]


def test_explicit_20_minute_rule_still_supported():

    observations = pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-01-01T00:00:00Z",
            "2025-01-01T00:15:00Z",
            "2025-01-01T00:45:00Z",
        ]),
        "Stage_ft": [8.0, 8.2, 8.5],
    })

    segmented, summary = segment_stage_observations(
        observations,
        expected_interval_minutes=20,
    )

    assert len(summary) == 2
    assert summary["observations"].tolist() == [2, 1]
