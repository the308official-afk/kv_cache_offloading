# Cache Value Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Highest-value phase | execution | SPECULATIVE |
| Lowest-value phase | patch_generation | SPECULATIVE |
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
| execution | MEASURED | 0 | MEASURED | 0.8975 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 1.0000 | DERIVED | 1.0000 | DERIVED | 0.5213 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| planning | MEASURED | 0 | MEASURED | 0.9005 | DERIVED | 0.5000 | DERIVED | 0.3500 | SPECULATIVE | 0.4500 | SPECULATIVE | 0.6120 | DERIVED | 0.7701 | DERIVED | 0.4829 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| review | MEASURED | 0 | MEASURED | 0.9360 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 0.2514 | DERIVED | 0.6001 | DERIVED | 0.4453 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| patch_generation | MEASURED | 0 | MEASURED | 0.9352 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 0.1048 | DERIVED | 0.5908 | DERIVED | 0.4198 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
