
"""Statistical candidate stage thresholds for USGS peak analysis.

The threshold method reproduces the existing
median_baseflow_densest_1ft_window_top_200_peaks methodology.

NOAA Action Stage is optional comparison information.
It is not required for threshold calculation.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


THRESHOLD_METHOD = "median_baseflow_densest_1ft_window_top_200_peaks"


def analyze_stage_baseflow_window(
    selected_events: pd.DataFrame,
    window_width_ft: float = 1.0,
) -> dict[str, Any]:
    """Find the densest baseline interval among selected peaks.

    Preserves the original ascending-order, first-densest
    tie-breaking rule. Both interval endpoints are included.
    """
    width = float(window_width_ft)

    if not np.isfinite(width) or width <= 0:
        raise ValueError("Window width must be finite and positive.")

    if "baseflow_peak" not in selected_events:
        raise ValueError("Selected events lack baseflow_peak.")

    values = pd.to_numeric(
        selected_events["baseflow_peak"],
        errors="coerce",
    ).to_numpy(dtype=float)

    values = np.sort(values[np.isfinite(values)])

    if len(values) == 0:
        return {
            "status": "no_valid_baseflow",
            "number_of_events": int(len(selected_events)),
            "number_of_valid_baseflows": 0,
        }

    left = 0
    best_left = best_right = 0

    for right in range(len(values)):
        while values[right] - values[left] > width:
            left += 1

        if right - left > best_right - best_left:
            best_left, best_right = left, right

    chosen = values[best_left:best_right + 1]

    return {
        "status": "ok",
        "number_of_events": int(len(selected_events)),
        "number_of_valid_baseflows": int(len(values)),
        "window_width_ft": width,
        "window_min_ft": float(chosen.min()),
        "window_max_ft": float(chosen.max()),
        "events_in_window": int(len(chosen)),
        "fraction_in_window": float(
            len(chosen) / len(values)
        ),
        "median_all_baseflow_ft": float(np.median(values)),
        "median_window_baseflow_ft": float(np.median(chosen)),
        "tie_breaking": (
            "first densest interval in ascending baseflow order"
        ),
    }


def filter_peaks_by_candidate_threshold(
    top_peaks: pd.DataFrame,
    window_width_ft: float = 1.0,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Calculate the candidate threshold and filter observed peaks.

    The threshold is derived from valid baseline values.
    All selected peak candidates are then evaluated using
    their observed stage, including isolated observations
    without baseline estimates.
    """
    if "flow_peak" not in top_peaks:
        raise ValueError("Selected peaks lack flow_peak.")

    analysis = analyze_stage_baseflow_window(
        top_peaks,
        window_width_ft=window_width_ft,
    )

    if analysis["status"] != "ok":
        return top_peaks.iloc[0:0].copy(), analysis

    threshold = analysis["median_window_baseflow_ft"]

    filtered = top_peaks.loc[
        pd.to_numeric(top_peaks["flow_peak"], errors="coerce")
        >= threshold
    ].copy()

    analysis["threshold_method"] = THRESHOLD_METHOD
    analysis["significant_stage_threshold_candidate_ft"] = threshold
    analysis["threshold_for_peak_filter_ft"] = threshold
    analysis["threshold_peak_filter_rule"] = (
        "observed_peak_stage_ft >= threshold_for_peak_filter_ft"
    )
    analysis["threshold_mrms_validated"] = False
    analysis["validation_status"] = "candidate_for_testing_only"
    analysis["filtered_peak_count"] = int(len(filtered))

    return filtered, analysis
