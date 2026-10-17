
"""Tests for the reusable USGS stage peak pipeline."""

import pandas as pd
import pytest

from usgs_stage_peaks.pipeline import process_stage_station


def sample_stage():
    return pd.DataFrame({
        "datetime": pd.date_range(
            "2025-01-01",
            periods=12,
            freq="5min",
            tz="UTC",
        ),
        "Stage_ft": [
            8.0, 8.0, 8.1, 8.5,
            9.0, 8.6, 8.2, 8.0,
            8.1, 8.4, 8.2, 8.0,
        ],
    })


def test_pipeline_preserves_observations(tmp_path):
    data = sample_stage()

    result = process_stage_station(
        data,
        tmp_path,
        site_id="08165500",
        save_outputs=False,
    )

    assert len(result.filtered_stage) == len(data)
    assert result.manifest[
        "observation_preservation_verified"
    ] is True


def test_pipeline_with_action_stage(tmp_path):
    result = process_stage_station(
        sample_stage(),
        tmp_path,
        site_id="08165500",
        action_stage_ft=9.0,
        save_outputs=False,
    )

    comparison = result.action_stage_comparison

    assert comparison["action_stage_ft"] == 9.0
    assert comparison["status"] in {
        "comparison_available",
        "candidate_threshold_unavailable",
    }


def test_pipeline_without_action_stage(tmp_path):
    result = process_stage_station(
        sample_stage(),
        tmp_path,
        site_id="08165500",
        save_outputs=False,
    )

    assert result.action_stage_comparison[
        "status"
    ] == "action_stage_unavailable"


def test_pipeline_exports_files(tmp_path):
    process_stage_station(
        sample_stage(),
        tmp_path,
        site_id="08165500",
        save_outputs=True,
    )

    expected = [
        "segments.parquet",
        "filtered_stage.parquet",
        "detected_events.parquet",
        "peak_candidates.parquet",
        "top_200_peaks.parquet",
        "filtered_peaks.parquet",
        "candidate_threshold.json",
        "action_stage_comparison.json",
        "processing_manifest.json",
    ]

    for filename in expected:
        assert (tmp_path / filename).is_file()


def test_invalid_action_stage(tmp_path):
    with pytest.raises(ValueError):
        process_stage_station(
            sample_stage(),
            tmp_path,
            site_id="08165500",
            action_stage_ft=float("nan"),
            save_outputs=False,
        )