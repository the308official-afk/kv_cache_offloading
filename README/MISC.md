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
ls -lah /mnt/docker-data/dynamo_cache | head
du -sh /mnt/docker-data/dynamo_cache
find /mnt/docker-data/dynamo_cache -maxdepth 3 | head -50
```

```bash
cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker sh -lc '
strings /usr/local/lib/python3.12/dist-packages/dynamo/_core.abi3.so \
  | grep "worker.spec_prefill" \
  | sort -u
'
```

```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE=gh200
source runtime_instrumentation/dynamo_machine_profile.sh

DYNAMO_MODEL_PATH="Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8" \
DYNAMO_SERVED_MODEL_NAME="Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8" \
FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
./run_dynamo_single_host.sh start
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
