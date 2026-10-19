

"""Reusable USGS water-stage peak processing pipeline.

Combines the existing segmentation, filtering, event detection,
peak selection, and statistical candidate threshold modules.

NOAA/NWS Action Stage is optional comparison information.
It never influences the statistical candidate threshold.

No interpolation or resampling is performed.
"""

from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .segmentation import segment_stage_observations
from .filtering import filter_stage_segments
from .events import detect_stage_events
from .peaks import select_peak_candidates
from .action_stage import filter_peaks_by_candidate_threshold


@dataclass
class StagePeakResult:
    """Results from processing one USGS monitoring station."""

    site_id: str
    output_directory: Path

    segments: pd.DataFrame
    filtered_stage: pd.DataFrame
    detected_events: pd.DataFrame
    peak_candidates: pd.DataFrame
    top_200_peaks: pd.DataFrame
    filtered_peaks: pd.DataFrame

    threshold_analysis: dict
    action_stage_comparison: dict
    manifest: dict


def _compare_action_stage(
    threshold: float | None,
    action_stage_ft: float | None,
) -> dict:
    """Compare the candidate threshold against NOAA/NWS Action Stage."""

    if action_stage_ft is None:
        return {
            "status": "action_stage_unavailable",
            "action_stage_ft": None,
            "candidate_threshold_ft": threshold,
        }

    action = float(action_stage_ft)

    if not math.isfinite(action):
        raise ValueError("action_stage_ft must be finite.")

    if threshold is None:
        return {
            "status": "candidate_threshold_unavailable",
            "action_stage_ft": action,
            "candidate_threshold_ft": None,
        }

    difference = threshold - action

    return {
        "status": "comparison_available",
        "action_stage_ft": action,
        "candidate_threshold_ft": threshold,
        "signed_difference_ft": difference,
        "absolute_difference_ft": abs(difference),
        "candidate_above_action_stage": difference > 0,
        "candidate_below_action_stage": difference < 0,
        "candidate_equals_action_stage": difference == 0,
        "reference": "NOAA/NWS Action Stage",
        "validation_status": "comparison_only",
    }


def process_stage_station(
    observations: pd.DataFrame,
    output_directory: str | Path,
    *,
    site_id: str,
    action_stage_ft: float | None = None,
    max_interval_minutes: float = 60.0,
    baseflow_alpha: float = 0.987,
    top_n: int = 200,
    window_width_ft: float = 1.0,
    save_outputs: bool = True,
) -> StagePeakResult:
    """Process one USGS station using the complete scientific pipeline.

    Parameters
    ----------
    observations:
        Validated DataFrame with datetime and Stage_ft columns.
    output_directory:
        Directory where results are saved.
    site_id:
        USGS monitoring station identifier, preserved as a string.
    action_stage_ft:
        Optional NOAA/NWS Action Stage in feet, using a compatible
        gauge reference datum.
    max_interval_minutes:
        Maximum interval between consecutive observations within
        one continuous processing segment.
    baseflow_alpha:
        Lyne-Hollick recursive-filter coefficient.
    top_n:
        Maximum number of highest observed peak candidates.
    window_width_ft:
        Width of the densest filtered-baseline interval.
    save_outputs:
        Whether to export Parquet and JSON results.

    Returns
    -------
    StagePeakResult
        Complete in-memory results and processing metadata.
    """

    start_time = time.monotonic()

    site_id = str(site_id).strip()

    if not site_id:
        raise ValueError("site_id cannot be empty.")

    output_dir = Path(output_directory).expanduser()

    # --------------------------------------------------------
    # 1. Segment observations
    # --------------------------------------------------------

    segmented, segments = segment_stage_observations(
        observations,
        expected_interval_minutes=max_interval_minutes,
    )

    # --------------------------------------------------------
    # 2. Apply recursive filtering
    # --------------------------------------------------------

    filtered_stage = filter_stage_segments(
        segmented,
        alpha=baseflow_alpha,
    )

    # --------------------------------------------------------
    # 3. Detect stage events
    # --------------------------------------------------------

    detected_events = detect_stage_events(filtered_stage)

    # --------------------------------------------------------
    # 4. Select peak candidates
    # --------------------------------------------------------

    peak_candidates, top_peaks = select_peak_candidates(
        filtered_stage,
        detected_events,
        top_n=top_n,
    )

    # --------------------------------------------------------
    # 5. Calculate statistical candidate threshold
    # --------------------------------------------------------

    filtered_peaks, threshold_analysis = (
        filter_peaks_by_candidate_threshold(
            top_peaks,
            window_width_ft=window_width_ft,
        )
    )

    if threshold_analysis["status"] == "ok":
        threshold = float(
            threshold_analysis[
                "significant_stage_threshold_candidate_ft"
            ]
        )
    else:
        threshold = None

    # --------------------------------------------------------
    # 6. Optional NOAA/NWS Action Stage comparison
    # --------------------------------------------------------

    action_comparison = _compare_action_stage(
        threshold,
        action_stage_ft,
    )

    # --------------------------------------------------------
    # 7. Validate observation preservation
    # --------------------------------------------------------

    if len(filtered_stage) != len(observations):
        raise RuntimeError(
            "Observation preservation check failed."
        )

    if not observations.empty and not top_peaks.empty:
        observed_max = float(
            pd.to_numeric(
                observations["Stage_ft"],
                errors="raise",
            ).max()
        )

        selected_max = float(top_peaks["flow_peak"].max())

        if not math.isclose(
            observed_max,
            selected_max,
            rel_tol=0.0,
            abs_tol=1e-9,
        ):
            raise RuntimeError(
                "Maximum observed stage was not preserved "
                "among selected peak candidates."
            )

    # --------------------------------------------------------
    # 8. Processing manifest
    # --------------------------------------------------------

    manifest = {
        "schema_version": 1,
        "package": "usgs-stage-peaks",
        "site_id": site_id,
        "parameters": {
            "max_interval_minutes": max_interval_minutes,
            "baseflow_alpha": baseflow_alpha,
            "top_n": top_n,
            "window_width_ft": window_width_ft,
        },
        "counts": {
            "observations": int(len(observations)),
            "segments": int(len(segments)),
            "filtered_observations": int(
                filtered_stage["filter_applied"].sum()
            ),
            "detected_events": int(len(detected_events)),
            "peak_candidates": int(len(peak_candidates)),
            "top_selected": int(len(top_peaks)),
            "retained_peaks": int(len(filtered_peaks)),
        },
        "candidate_threshold_ft": threshold,
        "action_stage_comparison_status": action_comparison["status"],
        "observation_preservation_verified": True,
        "maximum_observed_stage_preserved": (
            not observations.empty and not top_peaks.empty
        ),
        "elapsed_seconds": time.monotonic() - start_time,
    }

    # --------------------------------------------------------
    # 9. Export outputs
    # --------------------------------------------------------

    if save_outputs:
        output_dir.mkdir(parents=True, exist_ok=True)

        outputs = {
            "segments.parquet": segments,
            "filtered_stage.parquet": filtered_stage,
            "detected_events.parquet": detected_events,
            "peak_candidates.parquet": peak_candidates,
            "top_200_peaks.parquet": top_peaks,
            "filtered_peaks.parquet": filtered_peaks,
        }

        for filename, dataframe in outputs.items():
            dataframe.to_parquet(
                output_dir / filename,
                index=False,
            )

        json_outputs = {
            "candidate_threshold.json": threshold_analysis,
            "action_stage_comparison.json": action_comparison,
            "processing_manifest.json": manifest,
        }

        for filename, payload in json_outputs.items():
            path = output_dir / filename

            with path.open("w", encoding="utf-8") as file:
                json.dump(
                    payload,
                    file,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )

    return StagePeakResult(
        site_id=site_id,
        output_directory=output_dir,
        segments=segments,
        filtered_stage=filtered_stage,
        detected_events=detected_events,
        peak_candidates=peak_candidates,
        top_200_peaks=top_peaks,
        filtered_peaks=filtered_peaks,
        threshold_analysis=threshold_analysis,
        action_stage_comparison=action_comparison,
        manifest=manifest,
    )
