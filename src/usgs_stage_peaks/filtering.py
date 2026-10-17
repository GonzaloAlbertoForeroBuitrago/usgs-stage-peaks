
"""Gap-aware Lyne-Hollick filtering for USGS water-stage observations.

The numerical filter follows Hydro-Event-Detector 0.1.0.
Each continuous segment is filtered independently.

No interpolation or synthetic observations are introduced.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import lfilter


def lyne_hollick_baseline(
    stage: np.ndarray,
    alpha: float = 0.987,
) -> np.ndarray:
    """Reproduce the Hydro-Event-Detector 0.1.0 filter.

    Parameters
    ----------
    stage:
        One continuous sequence of water-stage observations.
    alpha:
        Recursive filtering coefficient.

    Returns
    -------
    np.ndarray
        Filtered stage-based baseline.

    Notes
    -----
    This is a numerical baseline estimate, not measured
    groundwater baseflow or discharge.
    """
    values = np.asarray(stage, dtype=np.float64)

    if values.ndim != 1 or values.size < 2:
        raise ValueError("At least two stage observations are required.")

    if not np.isfinite(values).all():
        raise ValueError("Stage observations must be finite.")

    if not 0 < alpha < 1:
        raise ValueError("alpha must be between 0 and 1.")

    # Match the reference implementation exactly.
    b = [(1.0 + alpha) / 2.0]
    a = [1.0, -alpha]

    # Forward filtering
    forward_diff = np.diff(values, prepend=values[0])
    forward = lfilter(b, a, forward_diff)

    # Backward filtering
    backward_diff = np.diff(
        values[::-1],
        prepend=values[-1],
    )
    backward = lfilter(b, a, backward_diff)[::-1]

    # Stage-based baseline
    quick_stage = (forward + backward) / 2.0
    baseline = values - quick_stage

    return np.clip(baseline, 0, values)


def filter_stage_segments(
    segmented: pd.DataFrame,
    alpha: float = 0.987,
    min_segment_observations: int = 3,
) -> pd.DataFrame:
    """Apply the recursive filter independently to each segment.

    Short segments remain in the output with missing baseline
    values. All original observations are preserved.
    """
    required = {"datetime", "Stage_ft", "segment_id"}

    missing = required - set(segmented.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")

    if min_segment_observations < 3:
        raise ValueError(
            "min_segment_observations must be at least 3."
        )

    result = segmented.copy()

    if result["segment_id"].isna().any():
        raise ValueError("Missing segment identifiers.")

    if result["Stage_ft"].isna().any():
        raise ValueError("Missing stage measurements.")

    result["baseline_ft"] = np.nan
    result["quick_stage_ft"] = np.nan
    result["filter_applied"] = False

    for _, group in result.groupby("segment_id", sort=False):
        if len(group) < min_segment_observations:
            continue

        baseline = lyne_hollick_baseline(
            group["Stage_ft"].to_numpy(dtype=float),
            alpha=alpha,
        )

        result.loc[group.index, "baseline_ft"] = baseline
        result.loc[group.index, "quick_stage_ft"] = (
            group["Stage_ft"].to_numpy(dtype=float) - baseline
        )
        result.loc[group.index, "filter_applied"] = True

    if len(result) != len(segmented):
        raise RuntimeError("Observation count changed.")

    return result
