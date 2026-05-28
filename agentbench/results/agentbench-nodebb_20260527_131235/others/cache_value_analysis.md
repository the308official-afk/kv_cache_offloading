# Cache Value Analysis

## Summary
| Field | Value | Provenance |
| --- | --- | --- |
| Highest-value phase | execution | SPECULATIVE |
| Lowest-value phase | review | SPECULATIVE |
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
| execution | MEASURED | 0 | MEASURED | 0.8477 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 1.0000 | DERIVED | 1.0000 | DERIVED | 0.5074 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| planning | MEASURED | 0 | MEASURED | 0.8886 | DERIVED | 0.5000 | DERIVED | 0.3500 | SPECULATIVE | 0.4500 | SPECULATIVE | 0.6820 | DERIVED | 0.8304 | DERIVED | 0.4849 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| patch_generation | MEASURED | 0 | MEASURED | 0.9321 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 0.4284 | DERIVED | 0.7849 | DERIVED | 0.4539 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
| review | MEASURED | 0 | MEASURED | 0.8073 | DERIVED | 0.5000 | DERIVED | 0.4000 | SPECULATIVE | 0.4000 | SPECULATIVE | 0.2518 | DERIVED | 0.8650 | DERIVED | 0.3776 | SPECULATIVE | spill-or-recompute | SPECULATIVE |
