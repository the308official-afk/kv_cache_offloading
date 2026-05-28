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
| planning | MEASURED | 0 | MEASURED | 11675 | MEASURED | high | DERIVED | 0.8886 | DERIVED | 0.4849 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| execution | MEASURED | 0 | MEASURED | 14059 | MEASURED | very high | DERIVED | 0.8477 | DERIVED | 0.5074 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
| patch_generation | MEASURED | 0 | MEASURED | 11035 | MEASURED | high | DERIVED | 0.9321 | DERIVED | 0.4539 | SPECULATIVE | nvme | SPECULATIVE | medium | SPECULATIVE | lower-value context; preserve only in colder storage if needed | SPECULATIVE |
| review | MEASURED | 0 | MEASURED | 12161 | MEASURED | very high | DERIVED | 0.8073 | DERIVED | 0.3776 | SPECULATIVE | nvme | SPECULATIVE | medium | SPECULATIVE | lower-value context; preserve only in colder storage if needed | SPECULATIVE |
