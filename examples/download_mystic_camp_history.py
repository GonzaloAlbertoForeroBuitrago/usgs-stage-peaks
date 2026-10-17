
"""Download historical USGS stage data for Mystic Camp.

Research example for the usgs-stage-peaks package.

Uses the existing mrms_usgs_events_2m.stage_download module.
No USGS downloader is reimplemented here.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd


RESEARCH_ROOT = Path.home() / "Documents" / "usgs_mrms_research"

DOWNLOADER_ROOT = RESEARCH_ROOT / "mrms_usgs_stage_research"

OUTPUT_ROOT = (
    RESEARCH_ROOT / "data" / "usgs_historical_2019_2026"
)

STATE = "TX"
SITE_ID = "08165500"

START_DATE = "2019-01-01"
END_DATE = "2026-10-17"  # Exclusive end (UTC)


def main() -> None:
    """Execute the existing USGS downloader and inspect results."""

    if not DOWNLOADER_ROOT.is_dir():
        raise FileNotFoundError(
            f"Downloader repository not found: {DOWNLOADER_ROOT}"
        )

    # The downloader is a separate research repository.
    # Make it importable without modifying either package.
    sys.path.insert(0, str(DOWNLOADER_ROOT))

    from mrms_usgs_events_2m.stage_download import (
        download_stage_data,
    )

    print("=" * 70, flush=True)
    print("MYSTIC CAMP — HISTORICAL USGS STAGE DOWNLOAD", flush=True)
    print("=" * 70, flush=True)

    print("Station:", SITE_ID, flush=True)
    print("Start:", START_DATE, flush=True)
    print("End (exclusive):", END_DATE, flush=True)
    print("Output:", OUTPUT_ROOT, flush=True)

    start = time.monotonic()

    result = download_stage_data(
        state=STATE,
        site_id=SITE_ID,
        start_date=START_DATE,
        end_date=END_DATE,
        output_root=OUTPUT_ROOT,
        save_raw_observations=False,
        save_raw_metadata=True,
    )

    elapsed = time.monotonic() - start

    data_dir = (
        OUTPUT_ROOT / STATE / SITE_ID / "downloaded_data"
    )

    print("\n" + "=" * 70, flush=True)
    print("DOWNLOAD SUMMARY", flush=True)
    print("=" * 70, flush=True)

    print("Source:", result.source, flush=True)
    print("Total observations:", len(result.observations), flush=True)
    print(
        "HydroEventDetector input:",
        len(result.hydroeventdetector_input),
        flush=True,
    )
    print(
        "Excluded observations:",
        len(result.excluded_observations),
        flush=True,
    )

    # Verify saved data independently.
    parquet_path = data_dir / "stage_hydroeventdetector.parquet"

    observations = pd.read_parquet(parquet_path)

    if not observations.empty:
        times = pd.to_datetime(
            observations["datetime"], utc=True
        )

        print("First observation:", times.min(), flush=True)
        print("Last observation:", times.max(), flush=True)

    manifest_path = data_dir / "download_manifest.json"

    with manifest_path.open("r", encoding="utf-8") as file:
        manifest = json.load(file)

    print(
        "Selected source:",
        manifest.get("selected_source"),
        flush=True,
    )
    print(
        "Fallback attempted:",
        manifest.get("fallback_attempted"),
        flush=True,
    )

    print(f"Elapsed time: {elapsed / 60:.2f} minutes", flush=True)
    print("Saved files:", data_dir, flush=True)


if __name__ == "__main__":
    main()
