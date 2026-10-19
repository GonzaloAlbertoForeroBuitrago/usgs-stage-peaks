
"""Validate the 60-minute segmentation rule using real USGS stations."""

from pathlib import Path
import time

import pandas as pd

from usgs_stage_peaks import process_stage_station, __version__


STAGE_ROOT = (
    Path.home()
    / ".tethys/Tethys_flood_2m/media/usgs_mrms_2m/app/stage_data"
)

OUTPUT_ROOT = (
    Path.home()
    / "Documents/usgs_mrms_research/outputs"
    / "stage_peaks_v020_validation"
)

STATIONS = [
    ("TEXAS", "08165500"),
    ("OKLAHOMA", "07335500"),
    ("ALABAMA", "02411600"),
    ("ALABAMA", "02362000"),
]


def main():
    print("=" * 75)
    print("USGS STAGE PEAKS — 60-MINUTE VALIDATION")
    print("Package version:", __version__)
    print("=" * 75)

    if __version__ != "0.2.0":
        raise RuntimeError(
            f"Expected package version 0.2.0, got {__version__}"
        )

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    records = []

    for state, site_id in STATIONS:
        start = time.monotonic()

        input_path = (
            STAGE_ROOT
            / state
            / site_id
            / "downloaded_data/stage_hydroeventdetector.parquet"
        )

        output_dir = OUTPUT_ROOT / state / site_id

        print(f"\nProcessing {state} {site_id}", flush=True)

        if not input_path.is_file():
            raise FileNotFoundError(input_path)

        observations = pd.read_parquet(input_path)

        result = process_stage_station(
            observations,
            output_dir,
            site_id=site_id,
            max_interval_minutes=60,
            baseflow_alpha=0.987,
            top_n=200,
            window_width_ft=1.0,
            save_outputs=True,
        )

        threshold = result.threshold_analysis.get(
            "significant_stage_threshold_candidate_ft"
        )

        maximum_observed = observations["Stage_ft"].max()
        maximum_selected = result.top_200_peaks["flow_peak"].max()

        record = {
            "site_id": site_id,
            "state": state,
            "observations": len(observations),
            "segments": len(result.segments),
            "detected_events": len(result.detected_events),
            "top_candidates": len(result.top_200_peaks),
            "retained_candidates": len(result.filtered_peaks),
            "threshold_ft": threshold,
            "maximum_observed_ft": maximum_observed,
            "maximum_selected_ft": maximum_selected,
            "maximum_preserved": (
                abs(maximum_observed - maximum_selected) < 1e-9
            ),
            "elapsed_seconds": round(
                time.monotonic() - start, 2
            ),
        }

        records.append(record)

        print("Segments:", record["segments"], flush=True)
        print("Detected events:", record["detected_events"], flush=True)
        print("Threshold:", threshold, flush=True)
        print(
            "Maximum observed preserved:",
            record["maximum_preserved"],
            flush=True,
        )

    summary = pd.DataFrame(records)

    summary.to_csv(
        OUTPUT_ROOT / "validation_summary.csv",
        index=False,
    )

    print("\n" + "=" * 75)
    print("VALIDATION SUMMARY")
    print("=" * 75)
    print(summary.to_string(index=False))
    print("\nOutput:", OUTPUT_ROOT)


if __name__ == "__main__":
    main()
