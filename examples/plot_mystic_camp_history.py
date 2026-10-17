
"""Generate historical Mystic Camp Plotly visualizations."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from usgs_stage_peaks.plotting import create_stage_peak_figure


ROOT = Path.home() / "Documents" / "usgs_mrms_research"

SITE_ID = "08165500"

OUTPUT_DIR = (
    ROOT
    / "data/stage_peaks_historical_2019_2026"
    / SITE_ID
)

PLOT_DIR = OUTPUT_DIR / "plots"


def main() -> None:

    # Load existing processed datasets.
    stage = pd.read_parquet(
        OUTPUT_DIR / "filtered_stage.parquet"
    )

    top_200 = pd.read_parquet(
        OUTPUT_DIR / "top_200_peaks.parquet"
    )

    filtered_peaks = pd.read_parquet(
        OUTPUT_DIR / "filtered_peaks.parquet"
    )

    with (
        OUTPUT_DIR / "candidate_threshold.json"
    ).open("r", encoding="utf-8") as file:
        threshold_analysis = json.load(file)

    threshold = threshold_analysis.get(
        "significant_stage_threshold_candidate_ft"
    )

    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # FIGURE 1 — TOP 200
    # ========================================================

    fig1 = create_stage_peak_figure(
        stage,
        top_200,
        site_id=SITE_ID,
        title="Historical Water Stage — Top 200 Peak Candidates",
        max_interval_minutes=20,
    )

    fig1.write_html(
        PLOT_DIR / "01_top_200_peaks.html",
        include_plotlyjs=True,
    )

    print("Saved: 01_top_200_peaks.html")

    # ========================================================
    # FIGURE 2 — FILTERED PEAKS
    # ========================================================

    fig2 = create_stage_peak_figure(
        stage,
        filtered_peaks,
        site_id=SITE_ID,
        title="Historical Water Stage — Filtered Peak Candidates",
        threshold_ft=threshold,
        max_interval_minutes=20,
    )

    fig2.write_html(
        PLOT_DIR / "02_filtered_peaks.html",
        include_plotlyjs=True,
    )

    print("Saved: 02_filtered_peaks.html")

    print("\nHistorical visualizations completed.")
    print("Output directory:", PLOT_DIR)


if __name__ == "__main__":
    main()
