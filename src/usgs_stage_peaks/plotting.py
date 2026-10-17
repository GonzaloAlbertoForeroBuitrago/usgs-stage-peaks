
"""Interactive Plotly visualization of USGS water-stage peak candidates.

Preserves observation gaps and generates standalone HTML figures.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go


def create_stage_peak_figure(
    observations: pd.DataFrame,
    peaks: pd.DataFrame,
    *,
    site_id: str,
    title: str,
    threshold_ft: float | None = None,
    max_interval_minutes: float = 20.0,
) -> go.Figure:
    """Plot historical stage and selected observed peak candidates.

    No interpolation or resampling is performed.
    """

    required_observations = {"datetime", "Stage_ft"}
    required_peaks = {"date_peak", "flow_peak"}

    if not required_observations.issubset(observations.columns):
        raise ValueError("Missing observation columns.")

    if not required_peaks.issubset(peaks.columns):
        raise ValueError("Missing peak columns.")

    data = observations.copy()

    data["datetime"] = pd.to_datetime(
        data["datetime"], utc=True
    )

    data["Stage_ft"] = pd.to_numeric(
        data["Stage_ft"], errors="coerce"
    )

    data = (
        data.dropna(subset=["datetime", "Stage_ft"])
        .sort_values("datetime")
        .reset_index(drop=True)
    )

    peak_data = peaks.copy()

    peak_data["date_peak"] = pd.to_datetime(
        peak_data["date_peak"], utc=True
    )

    # Insert explicit breaks where observation gaps exceed
    # the continuity threshold.
    gap_mask = (
        data["datetime"].diff()
        > pd.Timedelta(minutes=max_interval_minutes)
    )

    gap_positions = np.flatnonzero(gap_mask.to_numpy())

    times = data["datetime"].to_numpy()
    values = data["Stage_ft"].to_numpy(dtype=float)

    plot_times = np.insert(
        times,
        gap_positions,
        np.datetime64("NaT"),
    )

    plot_values = np.insert(
        values,
        gap_positions,
        np.nan,
    )

    fig = go.Figure()

    # Complete historical stage series.
    fig.add_trace(
        go.Scattergl(
            x=plot_times,
            y=plot_values,
            mode="lines",
            name="Observed Water Stage",
            line=dict(
                color="royalblue",
                width=1.2,
            ),
            connectgaps=False,
            hovertemplate=(
                "Date: %{x}<br>"
                "Stage: %{y:.2f} ft"
                "<extra></extra>"
            ),
        )
    )

    # Selected peak candidates.
    fig.add_trace(
        go.Scattergl(
            x=peak_data["date_peak"],
            y=peak_data["flow_peak"],
            mode="markers",
            name=f"Selected Peaks ({len(peak_data)})",
            marker=dict(
                color="red",
                size=7,
                symbol="circle",
            ),
            customdata=(
                peak_data["selected_rank"].to_numpy()
                if "selected_rank" in peak_data
                else None
            ),
            hovertemplate=(
                "Peak date: %{x}<br>"
                "Stage: %{y:.2f} ft"
                "<extra></extra>"
            ),
        )
    )

    # Statistical candidate threshold.
    if threshold_ft is not None:
        fig.add_hline(
            y=threshold_ft,
            line_dash="dash",
            line_color="darkorange",
            annotation_text=(
                f"Candidate threshold: {threshold_ft:.3f} ft"
            ),
            annotation_position="top left",
        )

    fig.update_layout(
        title=dict(
            text=f"USGS {site_id} — {title}",
            x=0.5,
        ),
        xaxis=dict(
            title="Datetime (UTC)",
            rangeslider=dict(
                visible=True,
                thickness=0.08,
            ),
        ),
        yaxis=dict(
            title="Gage Height (ft)",
        ),
        template="plotly_white",
        height=650,
        hovermode="closest",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(
            l=70,
            r=40,
            t=100,
            b=70,
        ),
    )

    return fig
