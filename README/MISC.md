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
cd ~/kv_cache_offloading

RUN_ID_ROOT="speculative_prefill_microbenchmark_20260710_151225"

find experiments/reports/speculative_prefill -maxdepth 2 -type f | grep "${RUN_ID_ROOT}" | sort

echo
echo "=== any runtime json at all? ==="
grep -Rni "RUNTIME_JSON" experiments/reports/speculative_prefill | grep "${RUN_ID_ROOT}" | head -40 || true

echo
echo "=== any spec-prefill text at all? ==="
grep -Rni "spec_prefill" experiments/reports/speculative_prefill | grep "${RUN_ID_ROOT}" | head -80 || true
```

```bash
cd ~/kv_cache_offloading

grep -Rni "worker.spec_prefill" \
  experiments/reports/speculative_prefill/speculative_prefill_microbenchmark_20260710_151225__sweep_* \
  || true
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
