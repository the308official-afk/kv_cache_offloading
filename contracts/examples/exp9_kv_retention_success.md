# Experiment 9 Worked Success Example

Source reports:

- behavior matrix: [`experiments/reports/latest_kv_retention_microbenchmark_matrix.csv`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports/latest_kv_retention_microbenchmark_matrix.csv)
- signal-rich older matrix: [`experiments/reports/misc/retention_threshold_matrix--worked.csv`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports/misc/retention_threshold_matrix--worked.csv)

## Behavioral Success

This is a real success pattern because both arms saw the same distractor
pressure, but only the protected arm kept request `A` warm.

```csv
arm,hint_profile,distractors,first_ms,replay_ms,replay_cached,replay_reuse,warm,warm_source,result
control,none,50,153,165,,,false,sglang_cache_events_fallback,control_row
protected,high-priority,50,151,70,448,0.959,true,response_usage_cached_tokens,effect_observed
```

Why this was a success:

- same distractor count: `50`
- control replay went cold: `warm=false`
- protected replay stayed warm: `warm=true`
- protected replay was much faster: `70 ms` vs `165 ms`

## Hint-Passing Proof

This is the signal-rich proof row that shows the protected request really
carried the priority hint.

```csv
hint_profile,worker_hint_status,worker_hint_profile_seen,request_agent_hints_priority_status,request_agent_hints_priority_values,survived_effective,reuse_signal
high-priority,full,high-priority,full,a_first:10|a_replay:10,true,true_reuse_hit
```

Columns to trust first:

- hint passed: `hint_profile`, `request_agent_hints_priority_status`, `request_agent_hints_priority_values`
- hint seen at worker: `worker_hint_status`, `worker_hint_profile_seen`
- hint helped behavior: `warm`, `replay_ms`, `replay_cached`, `replay_reuse`, `result`
