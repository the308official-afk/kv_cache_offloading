


./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
FRONTEND_IMAGE=local/dynamo-frontend:runtime-json-logs \
WORKER_IMAGE=local/dynamo-sglang:runtime-json-logs \
./run_dynamo_single_host.sh start




cd ~/kv_cache_offloading

python3 - <<'PY'
import json
import urllib.request

url = "http://127.0.0.1:8000/v1/chat/completions"
payload = {
    "model": "Qwen/Qwen2.5-Coder-7B-Instruct",
    "messages": [{"role": "user", "content": "Say hello in one word."}],
    "max_tokens": 4,
    "temperature": 0,
    "priority": 10,
}
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read().decode("utf-8")
        print("STATUS:", resp.status)
        print(body[:1000])
except Exception as e:
    print("REQUEST_FAILED:", e)
    if hasattr(e, "read"):
        try:
            print(e.read().decode("utf-8"))
        except Exception:
            pass
PY