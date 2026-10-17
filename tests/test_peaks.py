
"""Tests for observed stage peak candidate selection."""

import numpy as np
import pandas as pd
import pytest

from usgs_stage_peaks.peaks import select_peak_candidates


def sample_data():
    return pd.DataFrame({
        "datetime": pd.to_datetime([
            "2025-07-04T09:25:00Z",
            "2025-07-04T09:30:00Z",
            "2025-07-04T09:35:00Z",
            "2025-07-04T10:10:00Z",
            "2025-07-05T20:35:00Z",
            "2025-07-05T20:45:00Z",
            "2025-07-05T20:50:00Z",
            "2025-07-05T20:55:00Z",
        ]),
        "Stage_ft": [
            25.0, 27.0, 29.45, 37.52,
            8.89, 9.0, 9.3, 9.1,
        ],
        "segment_id": [1, 1, 1, 2, 3, 4, 4, 4],
        "baseline_ft": [
            24.0, 25.0, 26.0, np.nan,
            np.nan, 8.8, 8.9, 9.0,
        ],
        "filter_applied": [
            True, True, True, False,
            False, True, True, True,
        ],
    })


def test_isolated_peak_is_highest():
    data = sample_data()
    events = pd.DataFrame()

    all_peaks, top = select_peak_candidates(
        data, events, top_n=200
    )

    assert top.iloc[0]["flow_peak"] == pytest.approx(37.52)
    assert top.iloc[0]["candidate_type"] == "unfiltered_observation"
    assert not top.iloc[0]["baseline_available"]


def test_top_n_selection():
    all_peaks, top = select_peak_candidates(
        sample_data(), pd.DataFrame(), top_n=2
    )

    assert len(top) == 2
    assert top["flow_peak"].tolist() == [37.52, 29.45]


def test_no_duplicate_timestamps():
    all_peaks, _ = select_peak_candidates(
        sample_data(), pd.DataFrame()
    )

    assert all_peaks["date_peak"].is_unique


def test_invalid_top_n():
    with pytest.raises(ValueError):
        select_peak_candidates(
            sample_data(), pd.DataFrame(), top_n=0
        )


def test_detected_event_is_preserved():
    data = sample_data()

    events = pd.DataFrame([{
        "date_start": pd.Timestamp("2025-07-04T09:25:00Z"),
        "date_peak": pd.Timestamp("2025-07-04T09:30:00Z"),
        "date_end": pd.Timestamp("2025-07-04T09:35:00Z"),
        "flow_peak": 27.0,
        "baseflow_peak": 25.0,
        "event_volume": 24435.0,
        "baseflow_volume": 22500.0,
    }])

    all_peaks, _ = select_peak_candidates(data, events)

    detected = all_peaks.loc[
        all_peaks["candidate_type"] == "detected_event"
    ]

    assert len(detected) == 1
    assert detected.iloc[0]["flow_peak"] == pytest.approx(27.0)
    assert detected.iloc[0]["event_volume"] == pytest.approx(24435.0)
