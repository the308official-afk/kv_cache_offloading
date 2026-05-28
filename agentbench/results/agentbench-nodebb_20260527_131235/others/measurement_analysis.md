# Measurement Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Most prefill-heavy phase | execution | DERIVED |
| Strongest reuse phase | execution | DERIVED |
| Highest pressure phase | execution | DERIVED |
| Highest pressure risk | very high | DERIVED |
| Slowest phase | execution | DERIVED |
| Slowest phase latency (ms) | 120105.7190 | DERIVED |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Latency (ms) | Latency provenance | Input tokens | Input provenance | Output tokens | Output provenance | Cached input | Cached-input provenance | Finish | Finish provenance | Profile | Profile provenance | Reuse | Reuse provenance | Pressure | Pressure provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | 0 | MEASURED | 81913.5920 | MEASURED | 11675 | MEASURED | 1176 | MEASURED | 10176 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (10176 cached tokens) | DERIVED | high | DERIVED |
| execution | MEASURED | 0 | MEASURED | 120105.7190 | MEASURED | 14059 | MEASURED | 1432 | MEASURED | 10816 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (10816 cached tokens) | DERIVED | very high | DERIVED |
| patch_generation | MEASURED | 0 | MEASURED | 51450.8120 | MEASURED | 11035 | MEASURED | 1370 | MEASURED | 10816 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (10816 cached tokens) | DERIVED | high | DERIVED |
| review | MEASURED | 0 | MEASURED | 30244.8330 | MEASURED | 12161 | MEASURED | 856 | MEASURED | 8128 | MEASURED | stop | MEASURED | prefill-heavy | DERIVED | yes (8128 cached tokens) | DERIVED | very high | DERIVED |
