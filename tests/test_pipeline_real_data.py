
"""End-to-end integration test using Mystic Camp observations."""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from usgs_stage_peaks.segmentation import segment_stage_observations
from usgs_stage_peaks.filtering import filter_stage_segments
from usgs_stage_peaks.events import detect_stage_events
from usgs_stage_peaks.peaks import select_peak_candidates


DATA_PATH = (
    Path.home()
    / "Documents/usgs_mrms_research/data/usgs/TX/08165500"
    / "downloaded_data/stage_hydroeventdetector.parquet"
)


@pytest.mark.integration
def test_mystic_camp_complete_pipeline():

    if not DATA_PATH.is_file():
        pytest.skip("Mystic Camp dataset not available.")

    # 1. Load validated observations.
    observations = pd.read_parquet(DATA_PATH)

    # 2. Identify continuous segments.
    segmented, summary = segment_stage_observations(
        observations,
        expected_interval_minutes=5,
    )

    # 3. Apply independent recursive filtering.
    filtered = filter_stage_segments(
        segmented,
        alpha=0.987,
    )

    # 4. Detect events.
    events = detect_stage_events(filtered)

    # 5. Build and rank peak candidates.
    all_candidates, top_200 = select_peak_candidates(
        filtered,
        events,
        top_n=200,
    )

    # Verify observation preservation.
    assert len(filtered) == 733

    # Verify segmentation.
    assert summary["observations"].tolist() == [
        404, 1, 1, 327
    ]

    # Verify the maximum observed stage.
    assert filtered["Stage_ft"].max() == pytest.approx(37.52)

    # Verify that the isolated peak is retained.
    peak = top_200.loc[
        np.isclose(
            top_200["flow_peak"].to_numpy(dtype=float),
            37.52,
            rtol=0,
            atol=1e-6,
        )
    ]

    assert len(peak) == 1

    assert peak.iloc[0]["date_peak"] == pd.Timestamp(
        "2025-07-04T10:10:00Z"
    )

    # Verify unique peak timestamps.
    assert all_candidates["date_peak"].is_unique

    # Verify ranking.
    assert top_200["flow_peak"].is_monotonic_decreasing

    # Verify no candidate exceeds the observed maximum.
    assert top_200["flow_peak"].max() <= 37.52

    print("\nMystic Camp complete pipeline validated.")
    print("Detected events:", len(events))
    print("Peak candidates:", len(all_candidates))
    print("Selected top peaks:", len(top_200))
