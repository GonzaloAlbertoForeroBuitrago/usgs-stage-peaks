
"""USGS Stage Peaks.

Gap-aware detection and ranking of observed USGS water-stage
events for historical flood analysis.

Copyright 2026 Gonzalo Buitrago.
Licensed under the Apache License, Version 2.0.

The statistical candidate threshold is intended for scientific
evaluation and is not an operational flood-warning threshold.
"""

from importlib.metadata import PackageNotFoundError, version

from .segmentation import segment_stage_observations
from .filtering import lyne_hollick_baseline, filter_stage_segments
from .events import detect_stage_events
from .peaks import select_peak_candidates
from .action_stage import (
    analyze_stage_baseflow_window,
    filter_peaks_by_candidate_threshold,
)
from .plotting import create_stage_peak_figure
from .pipeline import StagePeakResult, process_stage_station


try:
    __version__ = version("usgs-stage-peaks")
except PackageNotFoundError:
    __version__ = "0+unknown"


__all__ = [
    "StagePeakResult",
    "process_stage_station",
    "segment_stage_observations",
    "lyne_hollick_baseline",
    "filter_stage_segments",
    "detect_stage_events",
    "select_peak_candidates",
    "analyze_stage_baseflow_window",
    "filter_peaks_by_candidate_threshold",
    "create_stage_peak_figure",
    "__version__",
]
