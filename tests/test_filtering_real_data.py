
"""Integration test for gap-aware filtering of Mystic Camp observations."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from usgs_stage_peaks.segmentation import segment_stage_observations
from usgs_stage_peaks.filtering import (
    filter_stage_segments,
    lyne_hollick_baseline,
)


DATA_PATH = (
    Path.home()
    / "Documents/usgs_mrms_research/data/usgs/TX/08165500"
    / "downloaded_data/stage_hydroeventdetector.parquet"
)


@pytest.mark.integration
def test_mystic_camp_filtering():

    if not DATA_PATH.is_file():
        pytest.skip("Mystic Camp dataset not available.")

    observations = pd.read_parquet(DATA_PATH)

    segmented, summary = segment_stage_observations(
        observations,
        expected_interval_minutes=5,
    )

    filtered = filter_stage_segments(
        segmented,
        alpha=0.987,
    )

    # All original observations must remain.
    assert len(filtered) == 733

    # Confirm continuous segment sizes.
    assert summary["observations"].tolist() == [
        404, 1, 1, 327
    ]

    # Filter only eligible continuous segments.
    assert filtered["filter_applied"].sum() == 731

    # Verify independent numerical filtering.
    for segment_id in [1, 4]:
        group = filtered.loc[
            filtered["segment_id"] == segment_id
        ]

        expected = lyne_hollick_baseline(
            group["Stage_ft"].to_numpy(),
            alpha=0.987,
        )

        np.testing.assert_allclose(
            group["baseline_ft"].to_numpy(),
            expected,
            rtol=1e-12,
            atol=1e-12,
        )

    # Isolated observations remain unfiltered.
    isolated = filtered.loc[
        filtered["segment_id"].isin([2, 3])
    ]

    assert len(isolated) == 2
    assert isolated["baseline_ft"].isna().all()
    assert (~isolated["filter_applied"]).all()

    # Preserve the observed July 4 flood peak.
    peak = filtered.loc[
        filtered["Stage_ft"].idxmax()
    ]

    assert peak["Stage_ft"] == pytest.approx(37.52)
    assert peak["segment_id"] == 2
    assert pd.isna(peak["baseline_ft"])
    assert not peak["filter_applied"]
