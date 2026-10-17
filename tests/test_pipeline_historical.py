
"""Historical integration test for the public station pipeline.

Uses previously downloaded Mystic Camp observations.
No API requests or downloads are performed.
"""

from pathlib import Path

import pandas as pd
import pytest

from usgs_stage_peaks.pipeline import process_stage_station


ROOT = Path.home() / "Documents" / "usgs_mrms_research"

DATA_PATH = (
    ROOT
    / "data/usgs_historical_2019_2026"
    / "TX/08165500/downloaded_data"
    / "stage_hydroeventdetector.parquet"
)


@pytest.mark.integration
def test_mystic_camp_historical_pipeline(tmp_path):

    if not DATA_PATH.is_file():
        pytest.skip("Historical Mystic Camp dataset unavailable.")

    observations = pd.read_parquet(DATA_PATH)

    result = process_stage_station(
        observations,
        tmp_path,
        site_id="08165500",
        max_interval_minutes=20,
        baseflow_alpha=0.987,
        top_n=200,
        window_width_ft=1.0,
        save_outputs=True,
    )

    assert len(result.filtered_stage) == 784452

    assert len(result.segments) == 45

    assert len(result.detected_events) == 58847

    assert len(result.peak_candidates) == 58936

    assert len(result.top_200_peaks) == 200

    assert len(result.filtered_peaks) == 127

    threshold = result.threshold_analysis[
        "significant_stage_threshold_candidate_ft"
    ]

    assert threshold == pytest.approx(
        8.25671154232561,
        abs=1e-9,
    )

    maximum_peak = result.top_200_peaks["flow_peak"].max()

    assert maximum_peak == pytest.approx(37.52)

    assert result.action_stage_comparison[
        "status"
    ] == "action_stage_unavailable"

    assert (
        tmp_path / "processing_manifest.json"
    ).is_file()

    print("\nHistorical public pipeline validated.")
    print("Observations:", len(result.filtered_stage))
    print("Segments:", len(result.segments))
    print("Detected events:", len(result.detected_events))
    print("Top candidates:", len(result.top_200_peaks))
    print("Retained candidates:", len(result.filtered_peaks))
    print("Candidate threshold:", threshold)
