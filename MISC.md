# Misc Debug Commands


```bash
* strict_priority is a real Dynamo scheduling signal that was missing from the original slide.

1. Scheduling
priority
latency_sensitivity
strict_priority

These answer:

How urgently should this request run?

priority: Moves important requests ahead and can influence SGLang KV eviction.
latency_sensitivity: Describes how damaging delay would be; the harness can convert it into priority.
strict_priority: Places requests into strict Dynamo router-queue tiers.
2. KV / Cache
prompt_cache_key
cache_control
cache_salt
speculative_prefill
iat
total_requests

These answer:

What cached state should we keep, isolate, remove or prepare?

prompt_cache_key: Identifies reusable prompt state.
cache_control: Controls retention type and TTL.
cache_salt: Separates cache namespaces between users or tenants.
speculative_prefill: Prepares likely next-turn KV early.
iat: Predicts how long KV may sit idle before the next request.
total_requests: Predicts how often the cached state will be reused.

This is why your suggestion about IAT is correct. Its most immediate practical value is helping the controller decide whether KV should remain in HBM, move to host memory or be prefetched later.

3. Routing / Worker
osl
backend_instance_id
prefill_worker_id
decode_worker_id
dp_rank

These answer:

Which worker should process this request?

osl: Predicts output length, helping Dynamo estimate the future load placed on a worker.
backend_instance_id: Selects a particular backend instance.
prefill_worker_id: Selects the prefill worker.
decode_worker_id: Selects the decode worker.
dp_rank: Selects a data-parallel replica.

OSL could affect scheduling indirectly, but Dynamo currently uses it primarily for resource estimation and routing, so this is the clearest bucket.

4. Affinity Identity
session_id
parent_session_id
prefix_id
traceparent

These answer:

Which agent, conversation, prefix or trace does this request belong to?

session_id: Identifies one agent reasoning chain.
parent_session_id: Connects a subagent to its parent.
prefix_id: Identifies requests expected to share a reusable prefix.
traceparent: Connects tracing information across the harness, Dynamo, SGLang and tools.

These identities do not automatically create affinity. A routing or cache policy must actively use them.
```




Core function	Simple explanation	Example
Routing and load balancing	Choose which worker handles a request.	Send it to a worker with useful cached conversation data and available capacity.
Queue scheduling	Decide which waiting request goes next.	Serve an urgent user request before a background report.
Prefill/decode coordination	Coordinate prompt processing and answer generation across separate workers.	Worker A processes the prompt; Worker B generates the answer.
KV-cache management and movement	Reuse and move cached computation to save repeated work.	Transfer a processed prompt’s cache to the worker generating the answer.
Resource planning and scaling	Adjust worker capacity to match demand.	Add prompt-processing workers when many long prompts arrive.





## Exp9 GH200 Priority Evidence Debug

Use this when Experiment 9 finishes but the decision proof shows weak priority
evidence, especially:

```text
sglang.priority=0
worker_prio_status=none
```

This checks where the high-priority signal disappeared.

### 1. Check The Matrix Priority Columns

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import csv
from pathlib import Path

p = Path("experiments/reports/latest_kv_retention_microbenchmark_matrix.csv")
rows = list(csv.DictReader(p.open()))

cols = [
    "distractors", "arm", "hint_profile",
    "req_prio_status", "req_prio_values",
    "worker_prio_status", "worker_prio_values",
    "first_ms", "replay_ms", "replay_cached", "replay_reuse",
    "survived", "effect_status",
]

print("\t".join(cols))
for r in rows:
    print("\t".join(str(r.get(c, "")) for c in cols))
PY
```

For protected rows, the good sign is:

```text
req_prio_status=full
req_prio_values=a_first:10|a_replay:10
```

### 2. Check The Raw Request Rows

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import csv
from pathlib import Path

matrix = list(csv.DictReader(Path("experiments/reports/latest_kv_retention_microbenchmark_matrix.csv").open()))
run_ids = sorted({r["run_id"] for r in matrix if r.get("run_id")})
root = Path("experiments/reports/retention_probe")

cols = [
    "cell", "request_role", "hint_profile",
    "agent_hints_priority",
    "top_level_priority_mode",
    "top_level_priority_sent",
    "top_level_priority_fallback_used",
    "top_level_priority_unsupported",
    "request_context_sent",
    "status",
    "latency_ms",
]

print("\t".join(cols))
for run_id in run_ids:
    for path in sorted(root.glob(f"{run_id}*/retention_probe_requests.csv")):
        for r in csv.DictReader(path.open()):
            if r.get("request_role") in {"a_first", "a_replay"}:
                print("\t".join([
                    path.parent.name,
                    r.get("request_role", ""),
                    r.get("hint_profile", ""),
                    r.get("agent_hints_priority", ""),
                    r.get("top_level_priority_mode", ""),
                    r.get("top_level_priority_sent", ""),
                    r.get("top_level_priority_fallback_used", ""),
                    r.get("top_level_priority_unsupported", ""),
                    r.get("request_context_sent", ""),
                    r.get("status", ""),
                    r.get("latency_ms", ""),
                ]))
PY
```

For protected rows, the good sign is:

```text
hint_profile=high-priority
agent_hints_priority=10
```

If protected rows do not show `10`, the problem is in the harness/request
construction.

### 3. Check Worker Logs Saw The Hints

```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
from pathlib import Path
import csv
import json

matrix_rows = list(csv.DictReader(Path("experiments/reports/latest_kv_retention_microbenchmark_matrix.csv").open()))
run_ids = sorted({r.get("run_id", "") for r in matrix_rows if r.get("run_id")})
logs = []
for run_id in run_ids:
    logs.extend(sorted(Path("experiments/reports/retention_probe_batches").glob(f"{run_id}*/*worker_runtime.log")))

print("run_ids:", " ".join(run_ids))
print("worker logs:", len(logs))

received = 0
with_hints = 0
with_priority = 0

for log in logs:
    for line in log.read_text(errors="replace").splitlines():
        if "[RUNTIME_JSON]" not in line:
            continue
        raw = line.split("[RUNTIME_JSON]", 1)[1].strip()
        try:
            event = json.loads(raw)
        except Exception:
            continue
        if event.get("event_type") != "worker.decode.request_received":
            continue
        received += 1
        hints = event.get("agent_hints")
        if hints:
            with_hints += 1
        if isinstance(hints, dict) and hints.get("priority") is not None:
            with_priority += 1

print("worker.decode.request_received:", received)
print("with agent_hints:", with_hints)
print("with agent_hints.priority:", with_priority)
PY
```

If `with agent_hints.priority` is `0`, Dynamo worker did not see the hint.

### 4. Check SGLang Priority Events

```bash
cd ~/kv_cache_offloading

grep -RniE '"event": ?"sglang.priority"|priority_hint_seen|scheduler_priority_applied' \
  experiments/reports/retention_probe_batches \
  experiments/raw/sglang_transfer_logs \
  | head -100
```

If this prints nothing, SGLang did not emit priority evidence for the run.

### 5. Check The Live Worker Has Priority Instrumentation

Run this while Dynamo is still up:

```bash
cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker python3 - <<'PY'
import importlib.util
from pathlib import Path

root = Path(importlib.util.find_spec("sglang").origin).resolve().parent
print("sglang root:", root)

for rel in [
    "srt/mem_cache/transfer_logging.py",
    "srt/mem_cache/radix_cache.py",
]:
    p = root / rel
    text = p.read_text(errors="replace") if p.exists() else ""
    print()
    print(p)
    print("exists:", p.exists())
    print("_sgl_log_priority_event:", "_sgl_log_priority_event" in text)
    print("priority_hint_seen:", "priority_hint_seen" in text)
    print("scheduler_priority_applied:", "scheduler_priority_applied" in text)
PY
```

Interpretation:

```text
request CSV has priority=10, but worker logs do not
```

Dynamo dropped the hint before worker decode.

```text
worker logs have agent_hints.priority, but sglang.priority=0
```

Dynamo saw the hint, but SGLang did not emit/apply priority evidence.

```text
SGLang instrumentation markers are missing
```

The live worker is not using the correctly patched SGLang overlay/image.

```text
markers exist, but no sglang.priority events
```

The hint arrived, but the priority cache/eviction path probably did not fire.
In that case, try more cache pressure after confirming the request path is good.
