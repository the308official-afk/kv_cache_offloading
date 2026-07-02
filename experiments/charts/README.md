# Manager-Facing Charts

This folder is the slide-ready surface for Experiments 9-12.

It should contain only:

- polished SVG charts
- the matrix CSV each chart was generated from

## Experiment 9: KV Retention

- `exp9_kvretention_matrix.csv`
  - one-row-per-sweep-arm matrix for the latest KV-retention microbenchmark
- `exp9_kvretention_latency_vs_distractors.svg`
  - replay latency as distractors increase
- `exp9_kvretention_cache_vs_distractors.svg`
  - replay cached tokens as distractors increase
- `exp9_kvretention_latency_gain_vs_distractors.svg`
  - how much faster the protected replay is than control
- `exp9_kvretention_cache_gain_vs_distractors.svg`
  - how many more cached tokens the protected replay keeps than control
- `exp9_kvretention_survival_vs_distractors.svg`
  - whether replay stays warm as distractors increase

## Experiment 10: Cache Pinning

- `exp10_cachepinning_matrix.csv`
  - latest cache-pinning microbenchmark matrix
- `exp10_cachepinning_validation_latency.svg`
  - doc-style validation latency for the two validation turns
- `exp10_cachepinning_validation_cache.svg`
  - doc-style validation cached-token reuse for the two validation turns
- `exp10_cachepinning_latency_vs_distractors.svg`
  - replay latency across the cache-pinning sweep
- `exp10_cachepinning_cache_vs_distractors.svg`
  - replay cached tokens across the cache-pinning sweep
- `exp10_cachepinning_latency_gain_vs_distractors.svg`
  - how much faster the pinned replay is than control
- `exp10_cachepinning_cache_gain_vs_distractors.svg`
  - how many more cached tokens the pinned replay keeps than control

## Experiment 11: Priority Scheduling

- `exp11_prioritysched_matrix.csv`
  - latest priority-scheduling microbenchmark matrix
- `exp11_prioritysched_priority_wins_vs_arrival_gap.svg`
  - how often late high-priority requests jumped ahead
- `exp11_prioritysched_wait_vs_arrival_gap.svg`
  - low-priority vs high-priority queue wait as arrival gap changes
- `exp11_prioritysched_wait_gain_vs_arrival_gap.svg`
  - how much less high-priority requests waited than low-priority requests
- `exp11_prioritysched_latency_vs_arrival_gap.svg`
  - low-priority vs high-priority end-to-end latency
- `exp11_prioritysched_latency_gain_vs_arrival_gap.svg`
  - how much faster high-priority requests finished than low-priority requests

## Experiment 12: Speculative Prefill

- `exp12_specprefill_matrix.csv`
  - latest speculative-prefill microbenchmark matrix
- `exp12_specprefill_latency_vs_warmup_wait.svg`
  - turn-B latency as warmup wait changes
- `exp12_specprefill_cache_vs_warmup_wait.svg`
  - turn-B cached tokens as warmup wait changes
- `exp12_specprefill_latency_gain_vs_warmup_wait.svg`
  - how much faster protected turn B is than control
- `exp12_specprefill_cache_gain_vs_warmup_wait.svg`
  - how many more cached tokens protected turn B gets than control

If a chart is missing, rerun the matching microbenchmark wrapper in `plot` or `all` mode.
