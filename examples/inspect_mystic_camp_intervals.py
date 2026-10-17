
"""Inspect historical USGS observation intervals by year."""

from pathlib import Path

import pandas as pd


ROOT = Path.home() / "Documents/usgs_mrms_research"

DATA_PATH = (
    ROOT
    / "data/usgs_historical_2019_2026/TX/08165500"
    / "downloaded_data/stage_hydroeventdetector.parquet"
)

data = pd.read_parquet(DATA_PATH)

data["datetime"] = pd.to_datetime(
    data["datetime"], utc=True
)

data = data.sort_values("datetime").reset_index(drop=True)

data["interval_minutes"] = (
    data["datetime"].diff().dt.total_seconds() / 60
)

data["year"] = data["datetime"].dt.year

print("=" * 70)
print("USGS HISTORICAL SAMPLING INTERVAL ANALYSIS")
print("=" * 70)

print("Total observations:", len(data))

print("\nMOST COMMON SAMPLING INTERVALS")
print(
    data["interval_minutes"]
    .value_counts()
    .head(15)
    .to_string()
)

print("\nSAMPLING INTERVALS BY YEAR")

for year, group in data.groupby("year"):

    print(f"\nYEAR {year}")
    print("Observations:", len(group))

    print(
        group["interval_minutes"]
        .value_counts()
        .head(5)
        .to_string()
    )

print("\nINTERVAL ANALYSIS COMPLETED")