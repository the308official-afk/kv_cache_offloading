# KV Hierarchy Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| GPU candidates | - | SPECULATIVE |
| CPU candidates | planning, execution | SPECULATIVE |
| NVMe candidates | patch_generation, review | SPECULATIVE |
| Drop candidates | - | SPECULATIVE |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Prompt tokens | Prompt-token provenance | Pressure | Pressure provenance | Reuse | Reuse provenance | Cache value | Cache-value provenance | Recommended tier | Tier provenance | Movement priority | Movement provenance | Reason | Reason provenance |
| --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | 0 | MEASURED | 9374 | MEASURED | high | DERIVED | 0.9005 | DERIVED | 0.4829 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| execution | MEASURED | 0 | MEASURED | 12172 | MEASURED | very high | DERIVED | 0.8975 | DERIVED | 0.5213 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| patch_generation | MEASURED | 0 | MEASURED | 7191 | MEASURED | high | DERIVED | 0.9352 | DERIVED | 0.4198 | SPECULATIVE | nvme | SPECULATIVE | medium | SPECULATIVE | lower-value context; preserve only in colder storage if needed | SPECULATIVE |
| review | MEASURED | 0 | MEASURED | 7305 | MEASURED | high | DERIVED | 0.9360 | DERIVED | 0.4453 | SPECULATIVE | nvme | SPECULATIVE | medium | SPECULATIVE | lower-value context; preserve only in colder storage if needed | SPECULATIVE |
