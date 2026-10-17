
"""Compare our event detector with HydroEventDetector 0.1.0."""

import numpy as np
import pandas as pd

from hydro_event_detector import HydroEventDetector

from usgs_stage_peaks.events import detect_stage_events
from usgs_stage_peaks.filtering import lyne_hollick_baseline


def test_reference_event_detection():

    # Continuous synthetic hydrograph.
    stage = np.array([
        8, 8, 8.5, 10, 13, 16, 12, 9, 8,
        8, 8.2, 10, 14, 18, 13, 9, 8, 8
    ], dtype=float)

    dates = pd.date_range(
        "2025-01-01",
        periods=len(stage),
        freq="5min",
    )

    # Reference HydroEventDetector.
    reference = HydroEventDetector(
        date_range=dates.to_numpy(),
        streamflow=stage,
    )

    reference.baseflow_lyne_hollick(alpha=0.987)
    reference.detect_events()
    reference.create_events_dataframe()

    # Our new implementation.
    baseline = lyne_hollick_baseline(stage, alpha=0.987)

    filtered = pd.DataFrame({
        "datetime": dates,
        "Stage_ft": stage,
        "baseline_ft": baseline,
        "segment_id": 1,
        "filter_applied": True,
    })

    actual = detect_stage_events(filtered)

    # Verify recursive filter equivalence.
    np.testing.assert_allclose(
        baseline,
        reference.baseflow,
        rtol=1e-12,
        atol=1e-12,
    )

    # Compare event indices.
    assert actual["i_start"].tolist() == reference.events["i_start"].tolist()
    assert actual["i_peak"].tolist() == reference.events["i_peak"].tolist()
    assert actual["i_end"].tolist() == reference.events["i_end"].tolist()

    # Compare observed event peaks.
    np.testing.assert_allclose(
        actual["flow_peak"].to_numpy(),
        reference.dataframe["flow_peak"].to_numpy(),
    )

    # Compare event volumes.
    np.testing.assert_allclose(
        actual["event_volume"].to_numpy(),
        reference.dataframe["event_volume"].to_numpy(),
        rtol=1e-12,
        atol=1e-12,
    )

    np.testing.assert_allclose(
        actual["baseflow_volume"].to_numpy(),
        reference.dataframe["baseflow_volume"].to_numpy(),
        rtol=1e-12,
        atol=1e-12,
    )