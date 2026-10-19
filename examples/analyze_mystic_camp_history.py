
"""Analyze historical Mystic Camp observations using usgs-stage-peaks.

Workflow
--------
1. Load validated USGS observations.
2. Segment observations using a maximum 60-minute interval.
3. Apply independent Lyne-Hollick recursive filtering.
4. Detect events and preserve original event metrics.
5. Select the 200 highest observed peak candidates.
6. Inspect baseline availability and candidate statistics.
7. Calculate the statistical candidate stage threshold.
8. Filter peaks using the candidate threshold.
9. Export processed datasets to Parquet and threshold metadata to JSON.

NOAA Action Stage is not required.
The calculated threshold is a research candidate, not an
operationally validated flood-warning threshold.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd

from usgs_stage_peaks.segmentation import segment_stage_observations
from usgs_stage_peaks.filtering import filter_stage_segments
from usgs_stage_peaks.events import detect_stage_events
from usgs_stage_peaks.peaks import select_peak_candidates
from usgs_stage_peaks.action_stage import (
    filter_peaks_by_candidate_threshold,
)


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path.home() / "Documents" / "usgs_mrms_research"

SITE_ID = "08165500"
STATE = "TX"

MAX_INTERVAL_MINUTES = 60
BASEFLOW_ALPHA = 0.987
TOP_N = 200
WINDOW_WIDTH_FT = 1.0

INPUT_PATH = (
    ROOT
    / "data"
    / "usgs_historical_2019_2026"
    / STATE
    / SITE_ID
    / "downloaded_data"
    / "stage_hydroeventdetector.parquet"
)

OUTPUT_DIR = (
    ROOT
    / "data"
    / "stage_peaks_historical_2019_2026"
    / SITE_ID
)


def main() -> None:
    start = time.monotonic()

    # ========================================================
    # 1. LOAD USGS OBSERVATIONS
    # ========================================================

    if not INPUT_PATH.is_file():
        raise FileNotFoundError(INPUT_PATH)

    observations = pd.read_parquet(INPUT_PATH)

    print("=" * 70, flush=True)
    print("USGS STAGE PEAKS — HISTORICAL ANALYSIS", flush=True)
    print("=" * 70, flush=True)

    print("Station:", SITE_ID, flush=True)
    print("State:", STATE, flush=True)
    print("Observations:", len(observations), flush=True)

    if observations.empty:
        raise ValueError("The historical dataset is empty.")

    # ========================================================
    # 2. GAP-AWARE SEGMENTATION
    # ========================================================

    segmented, summary = segment_stage_observations(
        observations,
        expected_interval_minutes=MAX_INTERVAL_MINUTES,
    )

    print("\nSEGMENTATION", flush=True)
    print("Continuous segments:", len(summary), flush=True)
    print(
        "Segments with at least 3 observations:",
        int((summary["observations"] >= 3).sum()),
        flush=True,
    )

    assert len(segmented) == len(observations)

    # ========================================================
    # 3. RECURSIVE FILTERING
    # ========================================================

    filtered = filter_stage_segments(
        segmented,
        alpha=BASEFLOW_ALPHA,
    )

    print("\nRECURSIVE FILTERING", flush=True)
    print(
        "Filtered observations:",
        int(filtered["filter_applied"].sum()),
        flush=True,
    )
    print(
        "Unfiltered observations:",
        int((~filtered["filter_applied"]).sum()),
        flush=True,
    )

    assert len(filtered) == len(observations)

    # ========================================================
    # 4. EVENT DETECTION
    # ========================================================

    events = detect_stage_events(filtered)

    print("\nEVENT DETECTION", flush=True)
    print("Detected events:", len(events), flush=True)

    # ========================================================
    # 5. PEAK CANDIDATE SELECTION
    # ========================================================

    all_candidates, top_200 = select_peak_candidates(
        filtered,
        events,
        top_n=TOP_N,
    )

    print("\nPEAK CANDIDATE SELECTION", flush=True)
    print("Total candidates:", len(all_candidates), flush=True)
    print("Top selected:", len(top_200), flush=True)

    print("\nTOP 10 OBSERVED PEAK CANDIDATES")

    print(
        top_200[
            [
                "selected_rank",
                "date_peak",
                "flow_peak",
                "candidate_type",
            ]
        ].head(10).to_string(index=False)
    )

    # ========================================================
    # 6. TOP 200 BASELINE ANALYSIS
    # ========================================================

    print("\n" + "=" * 70)
    print("TOP 200 PEAK BASELINE ANALYSIS")
    print("=" * 70)

    print("Selected candidates:", len(top_200))

    valid_baseline = top_200["baseflow_peak"].notna()

    print(
        "Candidates with baseline:",
        int(valid_baseline.sum()),
    )

    print(
        "Candidates without baseline:",
        int((~valid_baseline).sum()),
    )

    print("\nCANDIDATE TYPES")

    print(
        top_200["candidate_type"]
        .value_counts()
        .to_string()
    )

    print("\nBASELINE STATISTICS")

    if valid_baseline.any():
        print(
            top_200.loc[valid_baseline, "baseflow_peak"]
            .describe()
            .to_string()
        )
    else:
        print("No valid baseline estimates available.")

    print("\nPEAK STAGE STATISTICS")

    print(
        top_200["flow_peak"]
        .describe()
        .to_string()
    )

    # ========================================================
    # 7. STATISTICAL CANDIDATE THRESHOLD
    # ========================================================

    filtered_peaks, threshold_analysis = (
        filter_peaks_by_candidate_threshold(
            top_200,
            window_width_ft=WINDOW_WIDTH_FT,
        )
    )

    print("\n" + "=" * 70)
    print("STATISTICAL CANDIDATE THRESHOLD")
    print("=" * 70)

    print("Status:", threshold_analysis["status"])

    if threshold_analysis["status"] == "ok":

        threshold = threshold_analysis[
            "significant_stage_threshold_candidate_ft"
        ]

        print(
            "Candidate threshold (ft):",
            f"{threshold:.4f}",
        )

        print(
            "Window width (ft):",
            threshold_analysis["window_width_ft"],
        )

        print(
            "Window minimum (ft):",
            threshold_analysis["window_min_ft"],
        )

        print(
            "Window maximum (ft):",
            threshold_analysis["window_max_ft"],
        )

        print(
            "Baselines in densest window:",
            threshold_analysis["events_in_window"],
        )

        print(
            "Fraction in window:",
            threshold_analysis["fraction_in_window"],
        )

        print(
            "Median of all valid baselines (ft):",
            threshold_analysis["median_all_baseflow_ft"],
        )

        print(
            "Median within selected window (ft):",
            threshold_analysis["median_window_baseflow_ft"],
        )

        print(
            "Peaks retained after threshold:",
            len(filtered_peaks),
        )

        print(
            "Peaks excluded by threshold:",
            len(top_200) - len(filtered_peaks),
        )

        print(
            "MRMS validated:",
            threshold_analysis["threshold_mrms_validated"],
        )

    else:
        print(
            "Candidate threshold unavailable. "
            "No valid filtered baseline values were found."
        )

    # ========================================================
    # 8. VERIFY PEAK PRESERVATION
    # ========================================================

    print("\n" + "=" * 70)
    print("OBSERVED PEAK PRESERVATION")
    print("=" * 70)

    maximum_observed = float(observations["Stage_ft"].max())
    maximum_candidate = float(top_200["flow_peak"].max())

    print("Maximum observed stage (ft):", maximum_observed)
    print("Maximum selected candidate (ft):", maximum_candidate)

    if maximum_candidate != maximum_observed:
        raise RuntimeError(
            "The maximum observed stage was not preserved "
            "in the selected peak candidates."
        )

    print("Maximum observed stage preserved: YES")

    # ========================================================
    # 9. EXPORT DATASETS
    # ========================================================

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    outputs = {
        "segments.parquet": summary,
        "filtered_stage.parquet": filtered,
        "detected_events.parquet": events,
        "peak_candidates.parquet": all_candidates,
        "top_200_peaks.parquet": top_200,
        "filtered_peaks.parquet": filtered_peaks,
    }

    print("\n" + "=" * 70)
    print("EXPORTING DATASETS")
    print("=" * 70)

    for filename, dataframe in outputs.items():

        path = OUTPUT_DIR / filename

        dataframe.to_parquet(
            path,
            index=False,
        )

        print(f"Saved: {path.name}", flush=True)

    # Save complete threshold analysis.
    threshold_path = OUTPUT_DIR / "candidate_threshold.json"

    with threshold_path.open("w", encoding="utf-8") as file:
        json.dump(
            threshold_analysis,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print("Saved:", threshold_path.name)

    # ========================================================
    # 10. PROCESSING SUMMARY
    # ========================================================

    elapsed = time.monotonic() - start

    print("\n" + "=" * 70)
    print("HISTORICAL ANALYSIS COMPLETED")
    print("=" * 70)

    print("Station:", SITE_ID)
    print("Observations:", len(observations))
    print("Continuous segments:", len(summary))
    print("Detected events:", len(events))
    print("Total peak candidates:", len(all_candidates))
    print("Top selected:", len(top_200))
    print("Peaks retained after threshold:", len(filtered_peaks))

    print(f"Elapsed time: {elapsed:.2f} seconds")
    print("Output directory:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
