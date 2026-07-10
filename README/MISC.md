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
CUDA Version 12.9.1

Container image Copyright (c) 2016-2023, NVIDIA CORPORATION & AFFILIATES. All rights reserved.

This container image and its contents are governed by the NVIDIA Deep Learning Container License.
By pulling and using the container, you accept the terms and conditions of this license:
https://developer.nvidia.com/ngc/nvidia-deep-learning-container-license

A copy of this license is made available in this container at /NGC-DL-CONTAINER-LICENSE for your convenience.

/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
2026-07-10T15:50:52.723441Z  WARN __init__: dynamo.nixl_connect: Failed to load CuPy for GPU acceleration, utilizing numpy to provide CPU based             operations.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.cudart module is deprecated and will be removed in a future release, pleas            e switch to use the cuda.bindings.runtime module instead.
<frozen importlib._bootstrap_external>:1297: FutureWarning: The cuda.nvrtc module is deprecated and will be removed in a future release, please             switch to use the cuda.bindings.nvrtc module instead.
2026-07-10T15:50:56.304832Z  WARN encode_worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-10T15:50:56.305412Z  WARN worker_handler: Failed to import cupy, falling back to numpy: No module named 'cupy'.
2026-07-10T15:50:56.753442Z  WARN dynamo_llm::hub: Cannot connect to ModelExpress server: Transport error: transport error. Using direct downlo            ad.
2026-07-10T15:50:56.753474Z  INFO modelexpress_common::download: Downloading model 'Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8' using provider: Hugg            ing Face
2026-07-10T15:50:56.753606Z  INFO modelexpress_common::providers::huggingface: Using cache directory: "/home/dynamo/.cache/huggingface/hub"


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
