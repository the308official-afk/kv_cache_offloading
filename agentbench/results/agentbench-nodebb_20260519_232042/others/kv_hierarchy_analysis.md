# KV Hierarchy Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| GPU candidates | - | SPECULATIVE |
| CPU candidates | baseline_execution | SPECULATIVE |
| NVMe candidates | - | SPECULATIVE |
| Drop candidates | - | SPECULATIVE |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Prompt tokens | Prompt-token provenance | Pressure | Pressure provenance | Reuse | Reuse provenance | Cache value | Cache-value provenance | Recommended tier | Tier provenance | Movement priority | Movement provenance | Reason | Reason provenance |
| --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| baseline_execution | MEASURED | - | MEASURED | 26575 | MEASURED | very high | DERIVED | 0.9398 | DERIVED | 0.5331 | SPECULATIVE | cpu | SPECULATIVE | medium | SPECULATIVE | worth keeping, but cheaper off-GPU residency is acceptable | SPECULATIVE |
