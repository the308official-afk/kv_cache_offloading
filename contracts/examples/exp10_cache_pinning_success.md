# Experiment 10 Worked Success Example

Source report:

- [`experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv`](/Users/oluwolejaiyeoba/Documents/GitHub/kv_cache_offloading/experiments/reports/latest_cache_pinning_microbenchmark_matrix.csv)

## Validation Success

Experiment 10 has two levels of success. The first one is setup success:
the router must spawn the pin path and the worker must apply it.

```csv
part,row_kind,cache_control,ttl,turn,cache_hit,cached_tokens,router_pin,worker_pin,result
validate,validate_turn,ephemeral:1h,1h,turn1,miss,,spawned,applied,pin_path_applied_and_cache_reused
validate,validate_turn,ephemeral:1h,1h,turn2,hit,128,spawned,applied,pin_path_applied_and_cache_reused
```

Why this was a success:

- the cache-control TTL was really sent: `cache_control=ephemeral:1h`
- Dynamo really spawned the pin path: `router_pin=spawned`
- the worker really applied it: `worker_pin=applied`
- the second turn reused cache: `cache_hit=hit`, `cached_tokens=128`

## Sweep Success

This is the behavior you want after validation is already known to work.

```csv
arm,cache_control,distractors,first_ms,replay_ms,warm,replay_cached,reuse_signal
control,off,120,554,242,false,,no_reuse_evidence
protected,ephemeral:1h,120,551,164,true,832,true_reuse_hit
```

Why this was a success:

- same distractor pressure: `120`
- control turned cold: `warm=false`
- protected stayed warm: `warm=true`
- protected replay was faster: `164 ms` vs `242 ms`

Columns to trust first:

- pin path alive: `router_pin`, `worker_pin`, `result`
- cache-control really sent: `cache_control`
- retention effect: `warm`, `replay_ms`, `replay_cached`, `reuse_signal`

Note:

- in sweep rows, treat `router_pin` / `worker_pin` as less important than the
  validate rows
- always trust the validate rows first when checking whether the setup itself
  is correct
