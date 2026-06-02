# Runtime Hint Impact Pitch

This repo can now investigate how agentic runtime hints affect Dynamo/SGLang
serving behavior during realistic SWE-bench agent runs.

The core research question is:

> When I use hint profile X, does Dynamo/SGLang reuse more KV cache, move less
> KV data between GPU and CPU, improve TTFT, or schedule requests differently
> across agent phases such as planning, execution, patch generation, and review?

## What We Built

The setup connects three things that are usually separate:

```text
AgentBench phase/request -> Dynamo runtime logs -> SGLang KV cache movement
```

For every AgentBench request, the harness can attach:

- run id
- task id
- phase
- request id
- hint profile
- hint values

The instrumented Dynamo/SGLang path can then report:

- TTFT
- total latency
- cached tokens
- recomputed tokens
- cache reuse ratio
- scheduler cached blocks
- device-to-host KV transfers
- host-to-device KV reloads
- estimated KV MB moved
- transfer timing
- semantic token prefix when SGLang exposes it
- direct request attribution when request context reaches the transfer event

## Hint Profiles

Hint profiles are controlled request settings sent as `agent_hints`.

| Profile | Meaning | Main Fields |
| --- | --- | --- |
| `baseline` | Normal AgentBench behavior. Assumes software-engineering requests may reuse context and are moderately latency-sensitive. | `priority=5`, `reuse_likelihood=0.9`, `latency_sensitivity=0.7`, `expected_output_tokens=512` |
| `high-reuse` | Strongly suggests the request should benefit from existing KV/prefix reuse. | `priority=5`, `reuse_likelihood=1.0`, `latency_sensitivity=0.5`, `expected_output_tokens=512` |
| `low-reuse` | Suggests useful cache reuse is unlikely. | `priority=5`, `reuse_likelihood=0.0`, `latency_sensitivity=0.5`, `expected_output_tokens=512` |
| `high-priority` | Marks the request as important and latency-sensitive. | `priority=10`, `reuse_likelihood=0.5`, `latency_sensitivity=1.0`, `expected_output_tokens=512` |
| `low-priority` | Marks the request as less urgent. | `priority=1`, `reuse_likelihood=0.5`, `latency_sensitivity=0.2`, `expected_output_tokens=512` |
| `long-output` | Suggests the request may need a longer response. | `priority=5`, `reuse_likelihood=0.8`, `latency_sensitivity=0.5`, `expected_output_tokens=2048` |
| `short-output` | Suggests the request should produce a short response. | `priority=5`, `reuse_likelihood=0.8`, `latency_sensitivity=0.5`, `expected_output_tokens=128` |

The cleanest cache/scheduling comparisons are currently:

- `baseline` vs `high-reuse`
- `baseline` vs `low-reuse`
- `high-priority` vs `low-priority`
- `long-output` vs `short-output`

## What We Can Measure

For each profile and each agent phase, the reports can answer:

- Did TTFT improve?
- Did cached token count increase?
- Did recomputed token count decrease?
- Did cache reuse ratio improve?
- Did scheduler cached blocks change?
- Did we see more or fewer `device_to_host` transfers?
- Did we see `host_to_device` reloads?
- How much KV data moved?
- Which phase caused the transfers?
- Which request caused the transfers?
- Which token prefix was involved?

## Why This Matters

Without this setup, runtime hints are hard to evaluate because the benchmark
only shows final task output. This setup lets us look inside the serving path:

```text
hint profile -> request/phase -> scheduler/cache behavior -> transfer events
```

That means we can compare whether a hint profile changes real serving behavior,
not just whether the agent produces a different patch.

## Important Caveat

The reports can show strong evidence that hint profiles correlate with runtime
behavior. To prove the hints caused the behavior, Dynamo/SGLang must actually
consume those fields as controls, not only preserve them as labels.

So the current setup is best described as:

> A measurement and attribution harness for studying whether agentic runtime
> hints are associated with changes in KV reuse, scheduling, TTFT, and host/GPU
> KV movement.

The next stronger step is to run controlled profile comparisons and confirm
which hint fields are actively used by the runtime scheduler/cache policy.

