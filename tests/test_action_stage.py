
"""Tests for statistical candidate stage threshold calculation."""

import numpy as np
import pandas as pd
import pytest

from usgs_stage_peaks.action_stage import (
    analyze_stage_baseflow_window,
    filter_peaks_by_candidate_threshold,
)


def test_densest_window():
    data = pd.DataFrame({
        "baseflow_peak": [
            7.9, 8.0, 8.1, 8.2, 8.3, 12.0
        ],
    })

    result = analyze_stage_baseflow_window(data)

    assert result["status"] == "ok"
    assert result["events_in_window"] == 5
    assert result["median_window_baseflow_ft"] == pytest.approx(8.1)


def test_missing_baseline_is_excluded_from_calculation():
    data = pd.DataFrame({
        "baseflow_peak": [8.0, 8.1, np.nan, 8.2],
    })

    result = analyze_stage_baseflow_window(data)

    assert result["number_of_events"] == 4
    assert result["number_of_valid_baseflows"] == 3
    assert result["median_window_baseflow_ft"] == pytest.approx(8.1)


def test_isolated_peak_can_pass_threshold():
    data = pd.DataFrame({
        "flow_peak": [37.52, 9.0, 8.0],
        "baseflow_peak": [np.nan, 8.1, 8.0],
    })

    filtered, analysis = filter_peaks_by_candidate_threshold(data)

    assert analysis["status"] == "ok"
    assert analysis["threshold_mrms_validated"] is False

    assert 37.52 in filtered["flow_peak"].tolist()
    assert 8.0 not in filtered["flow_peak"].tolist()


def test_no_valid_baselines():
    data = pd.DataFrame({
        "flow_peak": [37.52, 29.45],
        "baseflow_peak": [np.nan, np.nan],
    })

    filtered, analysis = filter_peaks_by_candidate_threshold(data)

    assert analysis["status"] == "no_valid_baseflow"
    assert filtered.empty


def test_invalid_window_width():
    data = pd.DataFrame({
        "baseflow_peak": [8.0, 8.1, 8.2],
    })

    with pytest.raises(ValueError):
        analyze_stage_baseflow_window(
            data,
            window_width_ft=0,
        )
