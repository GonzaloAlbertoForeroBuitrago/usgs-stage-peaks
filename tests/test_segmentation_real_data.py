"""Integration test using real Mystic Camp USGS observations."""

from pathlib import Path

import pandas as pd
import pytest

from usgs_stage_peaks.segmentation import segment_stage_observations


RESEARCH_ROOT = (
    Path.home() / "Documents" / "usgs_mrms_research"
)

DATA_PATH = (
    RESEARCH_ROOT
    / "data/usgs/TX/08165500/downloaded_data"
    / "stage_hydroeventdetector.parquet"
)


@pytest.mark.integration
def test_mystic_camp_segmentation():

    if not DATA_PATH.is_file():
        pytest.skip("Mystic Camp dataset is not available.")

    observations = pd.read_parquet(DATA_PATH)

    segmented, summary = segment_stage_observations(
        observations,
        expected_interval_minutes=5,
    )

    # Verify observation preservation.
    assert len(segmented) == 733

    # Verify the four known continuous segments.
    assert len(summary) == 4

    assert summary["observations"].tolist() == [
        404, 1, 1, 327
    ]

    # Verify that the maximum observed stage is preserved.
    maximum_stage = segmented["Stage_ft"].max()

    assert maximum_stage == pytest.approx(37.52)

    peak = segmented.loc[
        segmented["Stage_ft"].idxmax()
    ]

    assert peak["segment_id"] == 2

    assert peak["datetime"] == pd.Timestamp(
        "2025-07-04T10:10:00Z"
    )