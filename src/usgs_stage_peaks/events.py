
"""Event detection for continuous USGS water-stage segments.

Reproduces the core event-boundary and event-metric calculations
from Hydro-Event-Detector 0.1.0, applied independently to each
continuous segment.

Event volumes are stage-time integrals (ft * seconds), not
physical discharge volumes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


EVENT_COLUMNS = [
    "segment_id",
    "i_start",
    "i_peak",
    "i_end",
    "date_start",
    "flow_start",
    "baseflow_start",
    "date_peak",
    "flow_peak",
    "baseflow_peak",
    "date_end",
    "flow_end",
    "baseflow_end",
    "month_num",
    "month_name",
    "event_volume",
    "baseflow_volume",
]


def _detect_segment_events(group: pd.DataFrame) -> pd.DataFrame:
    """Detect events in one continuous, already-filtered segment."""

    group = group.sort_values("datetime").reset_index(drop=True)

    stage = group["Stage_ft"].to_numpy(dtype=float)
    baseline = group["baseline_ft"].to_numpy(dtype=float)
    dates = pd.to_datetime(group["datetime"], utc=True)

    n = len(group)

    if n < 3:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    if not np.isfinite(stage).all() or not np.isfinite(baseline).all():
        raise ValueError("Filtered segment contains invalid values.")

    # Same event definition as HydroEventDetector.
    mask = stage > baseline
    changes = np.diff(mask.astype(int))

    # Preserve original crossing-index conventions.
    idx_start = np.where(changes == 1)[0]
    idx_end = np.where(changes == -1)[0] + 1

    if mask[0]:
        idx_start = np.insert(idx_start, 0, 0)

    if mask[-1]:
        idx_end = np.append(idx_end, n - 1)

    if len(idx_start) == 0 or len(idx_end) == 0:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    if idx_end[0] < idx_start[0]:
        idx_end = idx_end[1:]

    if len(idx_start) > len(idx_end):
        idx_start = idx_start[:len(idx_end)]

    # The original detector uses the median sampling interval
    # to calculate event and baseflow volumes.
    delta_seconds = float(
        np.median(
            np.diff(
                dates.to_numpy(dtype="datetime64[ns]")
            ).astype("timedelta64[s]").astype(float)
        )
    )

    events = []

    for i_start, i_end in zip(idx_start, idx_end):

        i_start = int(i_start)
        i_end = int(i_end)

        if i_end <= i_start:
            continue

        i_peak = i_start + int(
            np.argmax(stage[i_start:i_end + 1])
        )

        # Preserve original event-boundary exclusion behavior.
        if i_peak == i_start or i_peak == i_end:
            continue

        event_slice = slice(i_start, i_end + 1)

        peak_time = dates.iloc[i_peak]

        events.append({
            "segment_id": int(group["segment_id"].iloc[0]),
            "i_start": i_start,
            "i_peak": i_peak,
            "i_end": i_end,
            "date_start": dates.iloc[i_start],
            "flow_start": float(stage[i_start]),
            "baseflow_start": float(baseline[i_start]),
            "date_peak": peak_time,
            "flow_peak": float(stage[i_peak]),
            "baseflow_peak": float(baseline[i_peak]),
            "date_end": dates.iloc[i_end],
            "flow_end": float(stage[i_end]),
            "baseflow_end": float(baseline[i_end]),
            "month_num": int(peak_time.month),
            "month_name": peak_time.month_name(),
            "event_volume": float(
                np.sum(stage[event_slice]) * delta_seconds
            ),
            "baseflow_volume": float(
                np.sum(baseline[event_slice]) * delta_seconds
            ),
        })

    return pd.DataFrame(events, columns=EVENT_COLUMNS)


def detect_stage_events(filtered: pd.DataFrame) -> pd.DataFrame:
    """Detect events independently in all eligible segments.

    Parameters
    ----------
    filtered:
        Output of filter_stage_segments().

    Returns
    -------
    pd.DataFrame
        Detected events with original HydroEventDetector
        field names and segment identifiers.

    Notes
    -----
    Isolated observations remain in the original filtered
    dataset. They are not converted into artificial events.
    Their peak eligibility will be handled by peaks.py.
    """

    required = {
        "datetime",
        "Stage_ft",
        "segment_id",
        "baseline_ft",
        "filter_applied",
    }

    missing = required - set(filtered.columns)

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    results = []

    for _, group in filtered.groupby("segment_id", sort=True):

        if not group["filter_applied"].all():
            continue

        events = _detect_segment_events(group)

        if not events.empty:
            results.append(events)

    if not results:
        return pd.DataFrame(columns=EVENT_COLUMNS)

    return pd.concat(results, ignore_index=True)
