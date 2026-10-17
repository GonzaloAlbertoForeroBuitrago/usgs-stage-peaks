
"""Observed water-stage peak candidate selection.

Combines HydroEventDetector events with isolated and
segment-boundary maxima. No interpolation or gap merging.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def select_peak_candidates(
    filtered: pd.DataFrame,
    events: pd.DataFrame,
    top_n: int = 200,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build and rank observed stage peak candidates.

    Returns
    -------
    all_candidates:
        Unique candidates ranked by observed stage.
    top_candidates:
        Highest top_n candidates.
    """
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
        raise ValueError("top_n must be a positive integer.")

    required = {
        "datetime", "Stage_ft", "segment_id",
        "baseline_ft", "filter_applied",
    }
    missing = required - set(filtered.columns)
    if missing:
        raise ValueError(f"Missing observation columns: {sorted(missing)}")

    if filtered.empty:
        raise ValueError("No observations available.")

    data = filtered.copy()
    data["datetime"] = pd.to_datetime(
        data["datetime"], utc=True, errors="raise"
    )
    data["Stage_ft"] = pd.to_numeric(
        data["Stage_ft"], errors="raise"
    )
    data["baseline_ft"] = pd.to_numeric(
        data["baseline_ft"], errors="coerce"
    )

    if not np.isfinite(data["Stage_ft"].to_numpy()).all():
        raise ValueError("Invalid observed stage values.")

    if data["datetime"].duplicated().any():
        raise ValueError("Duplicate observation timestamps.")

    if data["segment_id"].isna().any():
        raise ValueError("Missing segment IDs.")

    data = data.sort_values("datetime").reset_index(drop=True)
    candidates = []

    # 1. Preserve original detected-event peaks and metrics.
    if not events.empty:
        required_events = {"date_peak", "flow_peak"}
        if not required_events.issubset(events.columns):
            raise ValueError("Missing event peak columns.")

        for _, event in events.iterrows():
            peak_time = pd.to_datetime(event["date_peak"], utc=True)

            matching = data.loc[data["datetime"] == peak_time]
            if len(matching) != 1:
                raise ValueError(
                    f"Event peak not found in observations: {peak_time}"
                )

            observed = matching.iloc[0]
            if not np.isclose(
                float(event["flow_peak"]),
                float(observed["Stage_ft"]),
            ):
                raise ValueError("Event peak disagrees with observations.")

            candidate = event.to_dict()
            candidate.update({
                "date_peak": peak_time,
                "flow_peak": float(observed["Stage_ft"]),
                "segment_id": int(observed["segment_id"]),
                "candidate_type": "detected_event",
                "baseline_available": bool(
                    pd.notna(observed["baseline_ft"])
                ),
            })
            candidates.append(candidate)

    # 2. Preserve maxima at both boundaries of each segment,
    #    and the maximum of every segment without filtering.
    for segment_id, group in data.groupby("segment_id", sort=True):
        group = group.sort_values("datetime")

        positions = set()

        # Segment boundaries are candidate observations.
        positions.add(group.index[0])
        positions.add(group.index[-1])

        # Preserve the segment's maximum observed stage.
        positions.add(group["Stage_ft"].idxmax())

        for position in sorted(positions):
            observation = data.loc[position]

            if not bool(observation["filter_applied"]):
                candidate_type = "unfiltered_observation"
            else:
                candidate_type = "segment_boundary_or_maximum"

            candidates.append({
                "segment_id": int(segment_id),
                "date_peak": observation["datetime"],
                "flow_peak": float(observation["Stage_ft"]),
                "baseflow_peak": (
                    float(observation["baseline_ft"])
                    if pd.notna(observation["baseline_ft"])
                    else np.nan
                ),
                "candidate_type": candidate_type,
                "baseline_available": bool(
                    pd.notna(observation["baseline_ft"])
                ),
            })

    result = pd.DataFrame(candidates)

    # 3. Prefer existing detected-event records when the
    #    same observation appears through multiple routes.
    priority = {
        "detected_event": 0,
        "unfiltered_observation": 1,
        "segment_boundary_or_maximum": 2,
    }

    result["_priority"] = result["candidate_type"].map(priority)

    result = (
        result.sort_values(
            ["_priority", "date_peak"],
            kind="mergesort",
        )
        .drop_duplicates(subset=["date_peak"], keep="first")
        .drop(columns="_priority")
    )

    # 4. Rank by observed stage, with earlier time breaking ties.
    result = (
        result.sort_values(
            ["flow_peak", "date_peak"],
            ascending=[False, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )

    result.insert(0, "selected_rank", range(1, len(result) + 1))

    top = result.head(top_n).copy().reset_index(drop=True)

    return result, top
