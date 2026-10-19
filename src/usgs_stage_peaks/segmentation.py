
"""Gap-aware segmentation of USGS water-stage observations.

Intervals up to 60 minutes are treated as continuous.
Longer intervals create independent filtering segments.

No interpolation or resampling is performed.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = ("datetime", "Stage_ft")


def segment_stage_observations(
    observations: pd.DataFrame,
    expected_interval_minutes: float = 60.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Divide observations into continuous processing segments.

    The interval parameter is the maximum permitted elapsed
    time between consecutive observations, in minutes.
    """

    if not isinstance(observations, pd.DataFrame):
        raise TypeError("observations must be a pandas DataFrame.")

    missing = [
        column for column in REQUIRED_COLUMNS
        if column not in observations.columns
    ]

    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if (
        not np.isfinite(expected_interval_minutes)
        or expected_interval_minutes <= 0
    ):
        raise ValueError(
            "expected_interval_minutes must be positive and finite."
        )

    data = observations.copy()

    data["datetime"] = pd.to_datetime(
        data["datetime"], utc=True, errors="coerce"
    )

    data["Stage_ft"] = pd.to_numeric(
        data["Stage_ft"], errors="coerce"
    )

    invalid = (
        data["datetime"].isna()
        | data["Stage_ft"].isna()
        | ~np.isfinite(data["Stage_ft"])
    )

    if invalid.any():
        raise ValueError(
            f"Input contains {int(invalid.sum())} invalid observations."
        )

    data = (
        data.sort_values("datetime", kind="mergesort")
        .reset_index(drop=True)
    )

    if data["datetime"].duplicated().any():
        raise ValueError("Duplicate observation timestamps detected.")

    max_interval = pd.Timedelta(
        minutes=expected_interval_minutes
    )

    data["time_difference"] = data["datetime"].diff()

    data["new_segment"] = (
        data["time_difference"].isna()
        | (data["time_difference"] > max_interval)
    )

    data["segment_id"] = (
        data["new_segment"].cumsum().astype("int64")
    )

    summary = (
        data.groupby("segment_id", sort=True)
        .agg(
            start=("datetime", "min"),
            end=("datetime", "max"),
            observations=("Stage_ft", "size"),
            minimum_stage_ft=("Stage_ft", "min"),
            maximum_stage_ft=("Stage_ft", "max"),
        )
        .reset_index()
    )

    summary["duration_hours"] = (
        summary["end"] - summary["start"]
    ).dt.total_seconds() / 3600

    summary["minimum_length_met"] = (
        summary["observations"] >= 3
    )

    assert summary["observations"].sum() == len(data)

    return data, summary

