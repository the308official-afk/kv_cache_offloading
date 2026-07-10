# Experiment 12 Worked Success Example

Source run:

- `speculative_prefill_microbenchmark_20260710_182813`

## Success Rows

```csv
sweep_value,arm,prompt_isolation_mode,turn_b_ms,turn_b_gain_ms,prefill_spawned,prefill_sent,prefill_done,prefill_target_seen,prefill_tokens,effect
1000,control,disjoint,10915,0,FALSE,FALSE,FALSE,FALSE,,baseline_off
1000,protected,disjoint,9715,1200,TRUE,TRUE,TRUE,TRUE,88189,faster_direct
```

Why this was a success:

- prompts were intentionally separated across sweep cells:
  `prompt_isolation_mode=disjoint`
- speculative prefill really ran:
  - `prefill_spawned=TRUE`
  - `prefill_sent=TRUE`
  - `prefill_done=TRUE`
  - `prefill_target_seen=TRUE`
- protected turn B was faster than control by `1200 ms`

Columns to trust first:

- hint enabled: `spec_prefill`
- decision path alive: `prefill_spawned`, `prefill_sent`, `prefill_done`, `prefill_target_seen`
- clean prompt separation: `prompt_isolation_mode`
- performance effect: `turn_b_ms`, `turn_b_gain_ms`, `effect`

Important note:

- control turn B can still reuse normal conversation state
- the real question is not "did control miss cache?"
- the real question is "did speculative prefill make protected turn B faster
  than the control arm?"
