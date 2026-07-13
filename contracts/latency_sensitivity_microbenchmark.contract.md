# Latency Sensitivity Microbenchmark Contract

This contract defines Experiment 13: Latency Sensitivity Probe.

The experiment reuses the proven priority-scheduling burst shape, but changes
the signal under test:

- Experiment 11 sends `nvext.agent_hints.priority`
- Experiment 13 sends `nvext.agent_hints.latency_sensitivity`

The main question is:

```text
When high-latency-sensitivity requests arrive after low-sensitivity requests,
does Dynamo/SGLang attach them earlier?
```

## Public Entrypoint

```text
agentbench/run_latency_sensitivity_microbenchmark_single_host.sh
```

## Required Runtime Stack

Use the same precise runtime stack as Experiment 11:

- prepared Dynamo source
- prepared SGLang overlay
- runtime JSON logging
- priority scheduling enabled on the worker
- `--enable-cache-report --enable-priority-scheduling --radix-eviction-policy priority`

## Main Knobs

```text
LATENCY_SENSITIVITY_MODE
LATENCY_SENSITIVITY_ID
LATENCY_SENSITIVITY_LOW_VALUE
LATENCY_SENSITIVITY_HIGH_VALUE
LOW_PRIORITY_COUNT
HIGH_PRIORITY_COUNT
PRIORITY_INPUT_LEN
PRIORITY_OUTPUT_LEN
PRIORITY_ARRIVAL_GAP_MS
PRIORITY_INTER_REQUEST_GAP_MS
PRIORITY_SCHEDULING_SWEEP_AXIS
PRIORITY_SCHEDULING_SWEEP_VALUES
PRIORITY_REQUEST_SOURCE
PRIORITY_SWEBENCH_DATASET
PRIORITY_SWEBENCH_SPLIT
PRIORITY_SWEBENCH_START_INDEX
EXPERIMENT_RESET_MODE
```

## Default Signal

```json
{
  "nvext": {
    "agent_hints": {
      "latency_sensitivity": 1.0
    }
  }
}
```

Low-sensitivity requests default to `0.2`.
High-sensitivity requests default to `1.0`.

## Main Outputs

```text
experiments/reports/latest_latency_sensitivity_microbenchmark_matrix.csv
experiments/reports/latest_latency_sensitivity_microbenchmark_summary.md
experiments/reports/latest_latency_sensitivity_microbenchmark_run_contract.json
experiments/reports/latest_latency_sensitivity_microbenchmark_jump_ahead.svg
experiments/charts/exp13_latencysens_matrix.csv
experiments/charts/exp13_latencysens_jump_ahead_vs_arrival_gap.svg
```

## Success Signals

The compact matrix should show:

```text
hint_kind=latency_sensitivity
hint_seen=yes
hint_path_status=worker_received_hint
high_jump_ahead_count > 0
result=latency_sensitivity_reordered
```

Simple reading:

- `hint_seen=yes`: the worker received the latency-sensitivity hint
- `high_jump_ahead_count > 0`: high-sensitivity requests moved ahead of earlier low-sensitivity requests
- `result=latency_sensitivity_reordered`: the run saw visible reorder behavior

If `hint_seen=yes` but `high_jump_ahead_count=0`, the hint arrived but did not
create visible scheduling movement in that run.
