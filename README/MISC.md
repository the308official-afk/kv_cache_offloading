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
ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker python3 - <<'PY'
import importlib.util
from pathlib import Path

root_spec = importlib.util.find_spec("sglang")
root = Path(root_spec.origin).resolve().parent
print("sglang root:", root)

targets = [
    root / "srt" / "mem_cache" / "transfer_logging.py",
    root / "srt" / "managers" / "cache_controller.py",
    root / "srt" / "mem_cache" / "hiradix_cache.py",
]

for path in targets:
    print("\nFILE:", path)
    if not path.exists():
        print("  exists: False")
        continue
    text = path.read_text(encoding="utf-8")
    print("  exists: True")
    print("  _sgl_log_priority_event:", "_sgl_log_priority_event" in text)
    print("  priority_hint_seen:", "priority_hint_seen" in text)
    print("  scheduler_priority_applied:", "scheduler_priority_applied" in text)
PY
sglang root: /workspace/sglang_transfer_overlay/sglang

FILE: /workspace/sglang_transfer_overlay/sglang/srt/mem_cache/transfer_logging.py
  exists: True
  _sgl_log_priority_event: False
  priority_hint_seen: False
  scheduler_priority_applied: False

FILE: /workspace/sglang_transfer_overlay/sglang/srt/managers/cache_controller.py
  exists: True
  _sgl_log_priority_event: False
  priority_hint_seen: False
  scheduler_priority_applied: False

FILE: /workspace/sglang_transfer_overlay/sglang/srt/mem_cache/hiradix_cache.py
  exists: True
  _sgl_log_priority_event: False
  priority_hint_seen: False
  scheduler_priority_applied: False
ojaiyeob@gracehopper:~/kv_cache_offloading$
```
