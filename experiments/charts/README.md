# Charts

This folder is the shared presentation-friendly output for the latest runs.

It is meant to contain only:
- chart SVGs
- the matrix CSVs those charts were generated from

## How To Read The Files

- `*_matrix.csv`
  - the main report table for that experiment
  - use this if you want the raw numbers behind the chart
- `*.svg`
  - slide-ready chart output
  - each one visualizes one specific effect

## Experiment 9: KV Retention

- `latest_kv_retention_microbenchmark_replay_latency.svg`
  - Shows how replay latency changes as distractor count increases.
  - Use it to see whether the protected request stays faster than control under pressure.
  - Lower replay latency means better retention/reuse.

- `latest_kv_retention_microbenchmark_replay_cached_tokens.svg`
  - Shows how many cached prompt tokens were available during replay.
  - Use it to see whether replay A was still warm in cache.
  - Higher cached-token count means stronger cache reuse.

- `latest_kv_retention_microbenchmark_survival_curve.svg`
  - Shows how long each profile stays warm as distractor count increases.
  - Use it to spot the eviction threshold.
  - A curve that stays high longer means the request survived cache pressure longer.

- `latest_kv_retention_microbenchmark_matrix.csv`
  - Raw per-run retention table behind the KV-retention charts.

## Experiment 10: Cache Pinning

- `latest_cache_pinning_microbenchmark_validation_latency.svg`
  - Shows the simple doc-style validation result: first request vs second request latency.
  - Use it to check whether the second request benefited from reuse after pinning was enabled.

- `latest_cache_pinning_microbenchmark_validation_cached_tokens.svg`
  - Shows cached-token reuse in the validation run.
  - Use it to confirm whether the second request came back with prompt-cache reuse.

- `latest_cache_pinning_microbenchmark_sweep_replay_latency.svg`
  - Shows replay latency across increasing distractor pressure for the cache-pinning sweep.
  - Use it to compare pinned vs control behavior as pressure rises.

- `latest_cache_pinning_microbenchmark_sweep_replay_cached_tokens.svg`
  - Shows replay cached-token counts across the cache-pinning sweep.
  - Use it to see whether pinning helped the protected prompt stay warm longer.

- `latest_cache_pinning_microbenchmark_matrix.csv`
  - Raw matrix behind the cache-pinning validation and sweep charts.

## Experiment 11: Priority Scheduling

- `latest_priority_scheduling_microbenchmark_attach_gain.svg`
  - Shows how much high-priority requests moved ahead of earlier low-priority requests.
  - Use it to answer: did high-priority work actually jump the line?
  - Bigger positive gain means stronger scheduling advantage for high-priority requests.

- `latest_priority_scheduling_microbenchmark_queue_wait.svg`
  - Shows queue-wait time for high-priority vs low-priority requests.
  - Use it to see whether high-priority requests spent less time waiting before service.
  - Lower queue wait for high-priority requests is the desired result.

- `latest_priority_scheduling_microbenchmark_matrix.csv`
  - Raw per-sweep matrix behind the priority-scheduling charts.
  - This file may appear after a fresh priority microbenchmark run generates its latest matrix.

## Experiment 12: Speculative Prefill

- `latest_speculative_prefill_microbenchmark_turnb_latency.svg`
  - Shows Turn B latency across the sweep axis.
  - Use it to see whether speculative prefill reduced the latency of the follow-up turn.
  - Lower Turn B latency is the main sign of benefit.

- `latest_speculative_prefill_microbenchmark_turnb_cached.svg`
  - Shows how many cached tokens were available for Turn B.
  - Use it to check whether Turn B reused more prompt state under the protected setting.

- `latest_speculative_prefill_microbenchmark_matrix.csv`
  - Raw per-run matrix behind the speculative-prefill charts.
  - This file may appear after a fresh speculative-prefill microbenchmark run generates its latest matrix.

## Quick Mental Model

- Latency charts answer: "Did this make the request faster?"
- Cached-token charts answer: "Did this keep more useful prompt state warm?"
- Survival/threshold charts answer: "How long did the protected request stay alive under pressure?"
- Scheduling charts answer: "Did high-priority work get served earlier?"
