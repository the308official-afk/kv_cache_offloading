# Experiment 11 Worked Success Example

Source report:

- [`experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv)

## Success Row

```csv
sweep_value,low_wait_ms,high_wait_ms,high_attach_leapfrogs,high_complete_leapfrogs,worker_hint_status,sglang_prio_status,effect
50,7972,3716,28,22,full,worker_received_hint,yes
```

Why this was a success:

- the worker saw the hint: `worker_hint_status=full`
- the SGLang side recorded the priority path: `sglang_prio_status=worker_received_hint`
- high-priority requests waited much less: `3716 ms` vs `7972 ms`
- high-priority requests leapfrogged low-priority ones:
  - attach leapfrogs: `28`
  - complete leapfrogs: `22`

Columns to trust first:

- hint passed and visible: `worker_hint_status`, `sglang_prio_status`
- scheduling effect: `low_wait_ms`, `high_wait_ms`, `high_attach_leapfrogs`, `high_complete_leapfrogs`
- summary verdict: `effect`

Simple read:

- if `high_wait_ms` is clearly below `low_wait_ms`, priority scheduling helped
- if leapfrogs are above `0`, the higher-priority requests actually moved ahead
