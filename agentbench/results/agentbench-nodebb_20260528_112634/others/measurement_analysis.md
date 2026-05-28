# Measurement Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Most prefill-heavy phase | execution | DERIVED |
| Strongest reuse phase | execution | DERIVED |
| Highest pressure phase | execution | DERIVED |
| Highest pressure risk | very high | DERIVED |
| Slowest phase | execution | DERIVED |
| Slowest phase latency (ms) | 15261.3510 | DERIVED |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Latency (ms) | Latency provenance | Input tokens | Input provenance | Output tokens | Output provenance | Cached input | Cached-input provenance | Finish | Finish provenance | Profile | Profile provenance | Reuse | Reuse provenance | Pressure | Pressure provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | 0 | MEASURED | 9339.7630 | MEASURED | 9374 | MEASURED | 8 | MEASURED | 8448 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8448 cached tokens) | DERIVED | high | DERIVED |
| execution | MEASURED | 0 | MEASURED | 15261.3510 | MEASURED | 12172 | MEASURED | 83 | MEASURED | 10880 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (10880 cached tokens) | DERIVED | very high | DERIVED |
| patch_generation | MEASURED | 0 | MEASURED | 1599.1140 | MEASURED | 7191 | MEASURED | 8 | MEASURED | 7104 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (7104 cached tokens) | DERIVED | high | DERIVED |
| review | MEASURED | 0 | MEASURED | 3837.0580 | MEASURED | 7305 | MEASURED | 6 | MEASURED | 7232 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (7232 cached tokens) | DERIVED | high | DERIVED |
