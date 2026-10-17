
# USGS Stage Peaks

Gap-aware detection, ranking, and statistical evaluation of observed
USGS water-stage peaks for historical flood analysis.

**Author:** Gonzalo Buitrago  
**License:** Apache License 2.0  
**Python:** 3.11+

## Overview

USGS Stage Peaks is a Python package for identifying significant
water-stage peak candidates from historical USGS monitoring stations.

The package preserves original observations, identifies discontinuities,
applies recursive filtering independently to continuous segments,
and selects the highest observed peak candidates.

It also calculates a statistical candidate stage threshold and
optionally compares that threshold with NOAA/NWS Action Stage.

The package is designed for:

- Historical flood research
- USGS water-stage analysis
- Nationwide station processing
- Statistical threshold evaluation
- Subsequent MRMS precipitation analysis
- Integration with scientific web applications

## Installation


## Installation

USGS Stage Peaks requires Python 3.11 or newer.

### Option 1 — Install using Micromamba (recommended)

Create a dedicated Python environment:

```bash
micromamba create -n usgs_stage_peaks \
  -c conda-forge python=3.11 pip -y
```

Activate the environment:

```bash
micromamba activate usgs_stage_peaks
```

Install USGS Stage Peaks from PyPI:

```bash
python -m pip install usgs-stage-peaks
```

All required dependencies, including NumPy, pandas,
SciPy, PyArrow, and Plotly, are installed automatically.

Verify the installation:

```bash
python -c "import usgs_stage_peaks; print(usgs_stage_peaks.__version__)"
python -m pip check
```

### Option 2 — Install with pip

If Python 3.11 or newer is already available:

```bash
python -m pip install usgs-stage-peaks
```

### Option 3 — Install from GitHub for development

Clone the repository:

```bash
git clone https://github.com/GonzaloAlbertoForeroBuitrago/usgs-stage-peaks.git
cd usgs-stage-peaks
```

Create and activate a development environment:

```bash
micromamba create -n usgs_stage_peaks_dev \
  -c conda-forge python=3.11 pip -y

micromamba activate usgs_stage_peaks_dev
```

Install the package with development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run the tests:

```bash
python -m pytest -v
```

Some integration tests require locally stored USGS
research datasets and are skipped when unavailable.

### Verify the public API

```python
import usgs_stage_peaks as usp

print("Version:", usp.__version__)
print("Pipeline available:", callable(usp.process_stage_station))
```


## Input data

The package accepts a pandas DataFrame containing:

| Column | Description |
|---|---|
| `datetime` | Observation timestamp |
| `Stage_ft` | Observed water stage in feet |

Example:

```python
import pandas as pd

observations = pd.read_parquet(
    "stage_hydroeventdetector.parquet"
)
```

The input must contain valid timestamps and finite water-stage values.

## Scientific methodology

### 1. Gap-aware segmentation

Observations are divided into continuous processing segments.

By default, consecutive observations separated by 20 minutes or
less remain in the same segment.

Intervals greater than 20 minutes create a new segment.

No interpolation or resampling is performed.

### 2. Recursive filtering

The Lyne–Hollick recursive filter is applied independently to
eligible continuous segments.

Default coefficient:

```python
alpha = 0.987
```

The filter produces a numerical stage baseline.

This is an experimental application of a recursive filtering
method originally developed for streamflow separation.

The filtered stage baseline should not be interpreted directly
as measured groundwater baseflow.

### 3. Event detection

Stage excursions above the filtered baseline are identified
within eligible continuous segments.

Event calculations preserve the existing HydroEventDetector
field names and event metrics, including volume-related fields.

The detected excursions are not necessarily independent
flood events.

### 4. Peak candidate selection

Observed stage peaks are ranked by their measured water level.

The default selection retains up to 200 highest candidates.

Isolated observations and segment-boundary maxima remain
eligible for selection.

Missing baseline estimates do not automatically disqualify
an observed peak.

### 5. Statistical candidate threshold

The threshold is calculated from valid filtered baseline
values associated with the selected peak candidates.

The algorithm:

1. Sorts valid baseline values in ascending order.
2. Identifies the densest interval with a maximum width of 1 ft.
3. Preserves the first-densest tie-breaking rule.
4. Calculates the median baseline within that interval.
5. Uses the median as the statistical candidate threshold.

The peak filtering rule is:

```python
observed_peak_stage_ft >= candidate_threshold_ft
```

The threshold is a research candidate, not an operational
flood-warning threshold.

### 6. Optional NOAA/NWS Action Stage comparison

If an official Action Stage reference is available, the package
can compare it with the calculated statistical candidate threshold.

The signed difference is:

```python
difference_ft = candidate_threshold_ft - action_stage_ft
```

Both values must use compatible units and gauge reference datums.

NOAA Action Stage is not required to calculate the statistical
candidate threshold.

Stations without Action Stage can still be processed.

## Usage

```python
import pandas as pd

from usgs_stage_peaks import process_stage_station

observations = pd.read_parquet(
    "stage_hydroeventdetector.parquet"
)

result = process_stage_station(
    observations,
    output_directory="outputs/08165500",
    site_id="08165500",
    action_stage_ft=None,
    max_interval_minutes=20,
    baseflow_alpha=0.987,
    top_n=200,
    window_width_ft=1.0,
)

print("Detected events:", len(result.detected_events))
print("Top candidates:", len(result.top_200_peaks))
print("Retained candidates:", len(result.filtered_peaks))

print(result.threshold_analysis)
print(result.action_stage_comparison)
```

## Output files

The pipeline produces:

| File | Description |
|---|---|
| `segments.parquet` | Continuous segment summary |
| `filtered_stage.parquet` | Observations and filtered baseline |
| `detected_events.parquet` | Detected stage excursions |
| `peak_candidates.parquet` | All ranked peak candidates |
| `top_200_peaks.parquet` | Highest selected candidates |
| `filtered_peaks.parquet` | Candidates retained after threshold filtering |
| `candidate_threshold.json` | Statistical threshold metadata |
| `action_stage_comparison.json` | Optional official threshold comparison |
| `processing_manifest.json` | Parameters and processing summary |

The `top_200_peaks.parquet` filename is retained for compatibility
with the current pipeline. The number of selected candidates
can be configured using `top_n`.

## Historical validation

The package has been tested using USGS station 08165500
with observations from January 2019 through October 2026.

Reference processing results:

| Metric | Result |
|---|---:|
| Observations | 784,452 |
| Continuous segments | 45 |
| Detected stage excursions | 58,847 |
| Peak candidates | 58,936 |
| Top selected candidates | 200 |
| Statistical candidate threshold | 8.25671154232561 ft |
| Retained candidates | 127 |
| Maximum observed stage | 37.52 ft |

These results establish computational reproducibility for the
reference dataset, not nationwide hydrological validity.

## Development and testing

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run automated tests:

```bash
python -m pytest -v
```

Some integration tests require locally stored USGS datasets.
They are skipped when those datasets are unavailable.

## To review

- Multiple candidates may correspond to the same flood episode.
- Statistical candidate thresholds require scientific validation. (Action Stage)
- NOAA/NWS Action Stage comparisons require compatible gauge datums. (Action Stage)


## License

Copyright 2026 Gonzalo Buitrago.

Licensed under the Apache License, Version 2.0.

See the LICENSE file for details.
