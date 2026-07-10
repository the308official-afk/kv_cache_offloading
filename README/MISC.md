

```bash
cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker sh -lc '
strings /usr/local/lib/python3.12/dist-packages/dynamo/_core.abi3.so \
  | grep "worker.spec_prefill" \
  | sort -u
'


ojaiyeob@gracehopper:~/kv_cache_offloading$ cd ~/kv_cache_offloading

docker exec -i dynamo-sglang-worker sh -lc '
strings /usr/local/lib/python3.12/dist-packages/dynamo/_core.abi3.so \
  | grep "worker.spec_prefill" \
  | sort -u
'
detected !Connected -> Connected state changetask received request requestexpired pull requestall branches are disabled and there is no else branchSpeculative prefill: sending next-turn prefixprefill_request_idprefill_prompt_tokensworker.spec_prefill.prefill_renderedspeculative_prefillworker.spec_prefill.prefill_completedresponse_channel_closedworker.spec_prefill.prefill_skippedworker.spec_prefill.prefill_failedSpeculative prefill failedinternal error: entered unreachable code: failed to match bindZMQ listener received cancellation signalFPM relay: failed to connectFPM relay: shutting downFPM relay: ZMQ stream endedforward-pass-metricsFPM direct publisher startedFPM direct publisher: shutting downConnection closed gracefullyConnection closed unexpectedly; issuing cancellationStream closed gracefullyStream closed unexpectedly; issuing cancellation/v1/realtime connection rejected: bidirectional engine not installedbidirectional engine not installed/v1/realtime engine.generate() failed/v1/realtime malformed JSON frame; closingmalformed JSON frame/v1/realtime received binary frame; not supported in this slicebinary frames not supported/v1/realtime inbound frame error; treating as disconnect/v1/realtime engine receiver dropped; ending inbound/v1/realtime serializing response chunk failed/v1/realtime client disconnected during responsestream completeAlready initializedScheduler output task cancelled, clearing active requestsMetrics publishing cancelled Simulating engine startup time:
hint_probe_idagent_hintsagent_hints_sourcenvext.agent_hintsrequest_contextcache_controlcache_control_sourcenvext.cache_controlruntime_observabilityllm_metricsmissing comments blockmalformed comments block - expected exactly 1 commentevent /opt/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:322dynamo_llm::preprocessor::speculative_prefillnum_tokens/opt/dynamo/lib/llm/src/preprocessor/speculative_prefill.rsevent /opt/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:253errorresponse_charsworker.spec_prefill.response_completeevent /opt/dynamo/lib/llm/src/preprocessor/speculative_prefill.rs:142event_typecomponentparent_run_idphasestep_titlespec_prefill_target_request_idspec_prefill_target_hint_probe_idspeculative_prefillinput_tokensoutput_tokenschunk_tokenscached_tokensprefill_worker_idprefill_dp_rankprefill_worker_typedecode_dp_rankdecode_worker_typedetokenize_total_latency
overflow adding duration to dateworker.spec_prefill.prefill_sentLORA load polling task cancelledMetrics background tasks started
ResponseFileSearchCallInProgressResponseReasoningSummaryPartDoneResponseReasoningSummaryTextDoneresponse.mcp_call_arguments.doneResponseCustomToolCallInputDeltaworker.spec_prefill.wrap_checkedworker.spec_prefill.task_spawnedpreprocessor.speculative_prefilluse_same_buffer_for_input_output
ojaiyeob@gracehopper:~/kv_cache_offloading$

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
