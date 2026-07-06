```bash
cd ~/kv_cache_offloading

# first sync latest repo/scripts from your laptop

./run_dynamo_single_host.sh stop || true

./runtime_instrumentation/prepare_instrumented_dynamo_source.sh

LEAN_FRONTEND=1 DYN_RUNTIME_JSON_LOGS=1 \
./runtime_instrumentation/build_instrumented_dynamo_images.sh
```



```bash
cd ~/kv_cache_offloading

export DYNAMO_MACHINE_PROFILE=ec2
source runtime_instrumentation/dynamo_machine_profile.sh

DYN_RUNTIME_JSON_LOGS=1 \
DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="Qwen/Qwen2.5-Coder-7B-Instruct" \
DYNAMO_SERVED_MODEL_NAME="Qwen/Qwen2.5-Coder-7B-Instruct" \
FRONTEND_IMAGE="$FRONTEND_IMAGE" \
WORKER_IMAGE="$WORKER_IMAGE" \
./run_dynamo_single_host.sh start
```



```bash
cd ~/kv_cache_offloading

python3 - <<'PY'
import urllib.request, urllib.error

url = "http://127.0.0.1:8000/clear_kv_blocks"
req = urllib.request.Request(url, data=b"{}", method="POST")
try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        print("STATUS:", resp.status)
        print(resp.read().decode())
except urllib.error.HTTPError as e:
    print("HTTP_ERROR:", e.code)
    print(e.read().decode())
except Exception as e:
    print("FAILED:", e)
PY
```




```bash

```




```bash

```
