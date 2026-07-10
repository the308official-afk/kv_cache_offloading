=== RESTART ===
first_ms	replay_ms
293	38
296	38
298	187
298	39

=== FLUSH ===
first_ms	replay_ms
296	38
71	37
70	184
74	37

```bash
benchmark_id	part	sweep_axis	sweep_value	run_id	model	arm	spec_prefill	turn_a_ms	turn_b_ms	turn_b_gain_ms	turn_b_cached	turn_b_reuse	hint_status	prefill_wrap	prefill_spawned	prefill_sent	prefill_done	prefill_target_seen	prefill_tokens	effect
speculative_prefill_microbenchmark_20260710_151225	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	0	speculative_prefill_microbenchmark_20260710_151225__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	566	292	0	8128	0.834	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_151225	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	0	speculative_prefill_microbenchmark_20260710_151225__sweep_1	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	451	336	-44	8128	0.834	on	missing	FALSE	FALSE	FALSE	FALSE		inferred_no_visible_gain
speculative_prefill_microbenchmark_20260710_151225	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	250	speculative_prefill_microbenchmark_20260710_151225__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	433	290	0	8128	0.834	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_151225	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	250	speculative_prefill_microbenchmark_20260710_151225__sweep_2	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	450	336	-46	8128	0.834	on	missing	FALSE	FALSE	FALSE	FALSE		inferred_no_visible_gain
speculative_prefill_microbenchmark_20260710_151225	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	500	speculative_prefill_microbenchmark_20260710_151225__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	control	FALSE	432	290	0	8128	0.834	off	missing	FALSE	FALSE	FALSE	FALSE		baseline_off
speculative_prefill_microbenchmark_20260710_151225	sweep	SPEC_PREFILL_WARMUP_WAIT_MS	500	speculative_prefill_microbenchmark_20260710_151225__sweep_3	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	protected	TRUE	450	336	-46	8128	0.834	on	missing	FALSE	FALSE	FALSE	FALSE		inferred_no_visible_gain


```

```bash
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

echo "=== HOST SGLang priority markers ==="
python3 - <<'PY'
from pathlib import Path

root = Path("upstream/sglang/python/sglang")
needles = ["_sgl_log_priority_event", "priority_hint_seen", "scheduler_priority_applied"]

print("root:", root.resolve())
for needle in needles:
    hits = []
    for p in root.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if needle in text:
            hits.append(str(p))
    print(f"\nNEEDLE: {needle}")
    print("count:", len(hits))
    for h in hits[:20]:
        print(h)
PY

echo
echo "=== WORKER SGLang priority markers ==="
docker exec -i dynamo-sglang-worker python3 - <<'PY'
import importlib.util
PY      print(h)s[:20]:(hits))")ncoding="utf-8")hint_seen", "scheduler_priority_applied"]
=== HOST SGLang priority markers ===
root: /home/central/ojaiyeob/kv_cache_offloading/upstream/sglang/python/sglang

NEEDLE: _sgl_log_priority_event
count: 1
upstream/sglang/python/sglang/srt/mem_cache/radix_cache.py

NEEDLE: priority_hint_seen
count: 0

NEEDLE: scheduler_priority_applied
count: 0

=== WORKER SGLang priority markers ===
root: /workspace/sglang_transfer_overlay/sglang

NEEDLE: _sgl_log_priority_event
count: 1
/workspace/sglang_transfer_overlay/sglang/srt/mem_cache/radix_cache.py

NEEDLE: priority_hint_seen
count: 0

NEEDLE: scheduler_priority_applied
count: 0
ojaiyeob@gracehopper:~/kv_cache_offloading$

```


```bash
cd ~/kv_cache_offloading

echo "=== HOST SGLang priority markers ==="
python3 - <<'PY'
from pathlib import Path

root = Path("upstream/sglang/python/sglang")
needles = ["_sgl_log_priority_event", "priority_hint_seen", "scheduler_priority_applied"]

print("root:", root.resolve())
for needle in needles:
    hits = []
    for p in root.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if needle in text:
            hits.append(str(p))
    print(f"\nNEEDLE: {needle}")
    print("count:", len(hits))
    for h in hits[:20]:
        print(h)
PY

echo
echo "=== WORKER SGLang priority markers ==="
docker exec -i dynamo-sglang-worker python3 - <<'PY'
import importlib.util
from pathlib import Path

root_spec = importlib.util.find_spec("sglang")
root = Path(root_spec.origin).resolve().parent
needles = ["_sgl_log_priority_event", "priority_hint_seen", "scheduler_priority_applied"]

print("root:", root)
for needle in needles:
    hits = []
    for p in root.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        if needle in text:
            hits.append(str(p))
    print(f"\nNEEDLE: {needle}")
    print("count:", len(hits))
    for h in hits[:20]:
        print(h)
PY
```
