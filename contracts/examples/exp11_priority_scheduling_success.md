# Experiment 11 Worked Success Example

Source report:

- [`experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports/latest_priority_scheduling_microbenchmark_matrix.csv)

## Success Row

```csv
gap_ms,low_requests,high_requests,max_jump_ahead,high_jump_ahead_count,high_jump_ahead_rate,high_completed_ahead_count,priority_hint_seen,priority_path_status,result
50,8,4,32,18,56.2%,14,yes,worker_received_hint,priority_reordered
```

Why this was a success:

- the worker saw the hint: `priority_hint_seen=yes`
- the priority path was visible: `priority_path_status=worker_received_hint`
- high-priority requests attached ahead of earlier low-priority requests:
  - `high_jump_ahead_count=18`
  - `high_jump_ahead_rate=56.2%`
- the final verdict is clear: `result=priority_reordered`

Columns to trust first:

- hint passed and visible: `priority_hint_seen`
- priority path evidence: `priority_path_status`
- scheduling effect: `high_jump_ahead_count`, `high_jump_ahead_rate`
- summary verdict: `result`

Simple read:

- if `high_jump_ahead_count > 0`, the higher-priority requests actually moved ahead
- if `high_jump_ahead_rate` is high, the scheduling effect is easier to show in a slide
