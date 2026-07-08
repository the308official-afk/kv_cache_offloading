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
docker logs -f dynamo-sglang-worker | egrep -i "prefill|cache|evict|hicache|warn|error"
```


```bash
while true; do
  date
  nvidia-smi --query-gpu=utilization.gpu,utilization.memory,memory.used,memory.total --format=csv,noheader
  sleep 2
done
```


```bash
while true; do
  date
  docker stats --no-stream dynamo-sglang-worker
  echo
  vmstat 1 2 | tail -1
  echo "----------------------------------------"
  sleep 2
done
```


```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
RETENTION_PROBE_ID="cachepin_debug_control_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
KV_TIER_MODES=gpu_cpu \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES=none \
CONTROL_CACHE_CONTROL_PROFILE=off \
PROTECTED_CACHE_CONTROL_PROFILES=off \
DISTRACTOR_COUNT=800 \
PROTECTED_INPUT_LEN=4000 \
DISTRACTOR_INPUT_LEN=400 \
EXPERIMENT_RESET_MODE=restart \
STOP_ON_PROBE_FAILURE=1 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```


```bash
cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
PRECISE_START_MODE=clean \
RETENTION_PROBE_ID="cachepin_debug_ephemeral_$(date +%Y%m%d_%H%M%S)" \
RETENTION_ATTRIBUTION_MODE=light \
KV_TIER_MODES=gpu_cpu \
CONTROL_HINT_PROFILE=none \
PROTECTED_HINT_PROFILES=none \
CONTROL_CACHE_CONTROL_PROFILE=ephemeral:1h \
PROTECTED_CACHE_CONTROL_PROFILES=ephemeral:1h \
DISTRACTOR_COUNT=800 \
PROTECTED_INPUT_LEN=4000 \
DISTRACTOR_INPUT_LEN=400 \
EXPERIMENT_RESET_MODE=restart \
STOP_ON_PROBE_FAILURE=1 \
./agentbench/run_kv_retention_probe_single_host.sh \
  Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
```


```bash

```




benchmark_id	part	row_kind	run_id	model	kv_tier	arm	turn	distractors	cache_control	ttl	http_status	latency_ms	prompt_tokens	cached_tokens	cache_hit	reuse_ratio	warm	first_ms	replay_ms	delta_ms	speedup_x	router_pin	worker_pin	worker_refreshes	req_cache_status	worker_cache_status	replay_evicts	replay_evict_status	result	reuse_signal
cache_pinning_microbenchmark_20260707_021550	validate	validate_turn	cache_pinning_microbenchmark_20260707_021550__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8		protected	turn1		ephemeral:1h	1h	200	762	30		miss							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_021550	validate	validate_turn	cache_pinning_microbenchmark_20260707_021550__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8		protected	turn2		ephemeral:1h	1h	200	1245	175	128	hit							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_021550	validate	validate_summary	cache_pinning_microbenchmark_20260707_021550__validate	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8		protected	turn2		ephemeral:1h	1h	200	1245		128	hit			762	1245			spawned	applied	0					pin_path_applied_and_cache_reused	doc_validation
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	60	off		200	75		1984	hit	0.97	TRUE	201	75	-126	2.68				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	60	ephemeral:1h		200	74		1984	hit	0.97	TRUE	201	74	-127	2.716				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	120	off		200	74		1984	hit	0.97	TRUE	198	74	-124	2.676				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	120	ephemeral:1h		200	78		1984	hit	0.97	TRUE	198	78	-120	2.538				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	200	off		200	76		1984	hit	0.97	TRUE	201	76	-125	2.645				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	200	ephemeral:1h		200	74		1984	hit	0.97	TRUE	201	74	-127	2.716				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	control	replay	240	off		200	74		1984	hit	0.97	TRUE	200	74	-126	2.703				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	protected	replay	240	ephemeral:1h		200	78		1984	hit	0.97	TRUE	204	78	-126	2.615				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_021550	sweep	sweep_compare	cache_pinning_microbenchmark_20260707_021550__sweep	Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8	gpu_cpu	compare			ephemeral:1h		complete												missing_runtime_json			missing_runtime_json			not_sent	inconclusive









```bash
python3 - <<'PY'
import csv
from pathlib import Path

path = Path("experiments/reports/latest_retention_probe_requests.csv")
rows = list(csv.DictReader(path.open()))

distractors = [r for r in rows if str(r.get("request_role","")).startswith("distractor_")]
reused = [r for r in distractors if str(r.get("cached_prompt_tokens","")).strip() not in {"", "0"}]

print("total_distractors:", len(distractors))
print("reused_distractors:", len(reused))

for r in reused[:20]:
    print(
        r["request_role"],
        "cached_prompt_tokens=", r.get("cached_prompt_tokens",""),
        "cache_reuse_ratio=", r.get("cache_reuse_ratio",""),
        "prompt_hash=", r.get("prompt_hash",""),
    )
PY
```





```bash
python3 - <<'PY'
import csv
from pathlib import Path
from collections import Counter

path = Path("experiments/reports/latest_retention_probe_requests.csv")
rows = list(csv.DictReader(path.open()))

distractors = [r for r in rows if str(r.get("request_role","")).startswith("distractor_")]
hashes = [r.get("prompt_hash","") for r in distractors]

print("total_distractors:", len(distractors))
print("unique_prompt_hashes:", len(set(hashes)))

dups = [item for item, count in Counter(hashes).items() if count > 1]
print("repeated_hashes:", len(dups))
if dups:
    print("example_repeated_hashes:", dups[:10])
PY
```




benchmark_id	part	row_kind	run_id	model	kv_tier	arm	turn	distractors	cache_control	ttl	http_status	latency_ms	prompt_tokens	cached_tokens	cache_hit	reuse_ratio	warm	first_ms	replay_ms	delta_ms	speedup_x	router_pin	worker_pin	worker_refreshes	req_cache_status	worker_cache_status	replay_evicts	replay_evict_status	result	reuse_signal
cache_pinning_microbenchmark_20260707_165021	validate	validate_turn	cache_pinning_microbenchmark_20260707_165021__validate	Qwen/Qwen2.5-Coder-7B-Instruct		protected	turn1		ephemeral:1h	1h	200	729	30		miss							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_165021	validate	validate_turn	cache_pinning_microbenchmark_20260707_165021__validate	Qwen/Qwen2.5-Coder-7B-Instruct		protected	turn2		ephemeral:1h	1h	200	694	175	128	hit							spawned	applied	0					pin_path_applied_and_cache_reused	
cache_pinning_microbenchmark_20260707_165021	validate	validate_summary	cache_pinning_microbenchmark_20260707_165021__validate	Qwen/Qwen2.5-Coder-7B-Instruct		protected	turn2		ephemeral:1h	1h	200	694		128	hit			729	694			spawned	applied	0					pin_path_applied_and_cache_reused	doc_validation
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	control	replay	600	off		200	43		832	hit	0.96	TRUE	128	43	-85	2.977				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	protected	replay	600	ephemeral:1h		200	42		832	hit	0.96	TRUE	128	42	-86	3.048				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	control	replay	800	off		200	44		832	hit	0.96	TRUE	128	44	-84	2.909				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	protected	replay	800	ephemeral:1h		200	32		832	hit	0.96	TRUE	291	32	-259	9.094				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	control	replay	1000	off		200	31		832	hit	0.96	TRUE	289	31	-258	9.323				full	missing_runtime_json	0	no_evict_seen	control_row	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_arm	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	protected	replay	1000	ephemeral:1h		200	31		832	hit	0.96	TRUE	290	31	-259	9.355				full	missing_runtime_json	0	no_evict_seen	not_sent	true_reuse_hit
cache_pinning_microbenchmark_20260707_165021	sweep	sweep_compare	cache_pinning_microbenchmark_20260707_165021__sweep	Qwen/Qwen2.5-Coder-7B-Instruct	gpu_cpu	compare			ephemeral:1h		complete												missing_runtime_json			missing_runtime_json			not_sent	inconclusive



2026-07-08T22:28:35.423499Z  WARN dynamo_llm::hub: Cannot connect to ModelExpress server: Transport error: transport error. Using direct download.
2026-07-08T22:28:35.423516Z  INFO modelexpress_common::download: Downloading model 'Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8' using provider: Hugging Face
2026-07-08T22:28:35.423543Z  INFO modelexpress_common::providers::huggingface: Using cache directory: "/home/dynamo/.cache/huggingface/hub"
2026-07-08T22:28:35.499385Z  INFO modelexpress_common::providers::huggingface: Downloaded model files for Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
2026-07-08T22:28:35.499429Z  INFO dynamo_llm::hub: ModelExpress download completed successfully for model: Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8
2026-07-08T22:28:35.504331Z  INFO _core: Registered base model 'Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8' MDC
2026-07-08T22:28:35.504441Z  INFO register._register_model_with_runtime_config: Successfully registered LLM with runtime config
2026-07-08T22:28:35.504473Z  INFO register.register_model_with_readiness_gate: Model registration succeeded; processing queued requests
2026-07-08T22:28:40.951251Z  INFO handle_payload: dynamo_runtime::pipeline::network::ingress::push_handler: request received request_id=a7d0086e-9a5b-4940-8b98-0026e75182df request_id="a7d0086e-9a5b-4940-8b98-0026e75182df" component="backend" endpoint="generate" namespace="dynamo" instance_id=7587894972260893829
2026-07-08T22:28:40.952068Z  INFO runtime_logging.emit_runtime_event: [RUNTIME_JSON] {"agent_hints":null,"agent_hints_keys":[],"agent_hints_source":"missing","cache_control":null,"cache_control_source":"missing","cache_control_ttl":null,"cache_control_type":null,"component":"worker.decode","event_type":"worker.decode.request_received","external_request_id":"a7d0086e-9a5b-4940-8b98-0026e75182df","hint_probe_id":null,"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8","request_context":null,"runtime_context_id":"a7d0086e-9a5b-4940-8b98-0026e75182df","serving_mode":"DisaggregationMode.AGGREGATED"}
2026-07-08T22:28:40.952194Z  WARN engine._resolve_routed_dp_rank: routed_dp_rank=0 is ignored because dp_size=1
[SGLANG_TRANSFER_JSON] {"action": "match_prefix", "cache_page_size": 64, "event": "sglang.cache", "function": "match_prefix", "semantic_token_count": 0, "semantic_token_ids_preview": [], "semantic_token_source": null, "timestamp": "2026-07-08T22:28:41.074279Z", "timestamp_ns": 1783549721074291795, "transfer_log_profile": "full", "worker_cache_control_seen": false, "worker_priority_seen": false}
[SGLANG_TRANSFER_JSON] {"action": "insert", "cache_page_size": 64, "cache_prefix_len": 0, "event": "sglang.cache", "function": "insert", "request_context_function": "cache_unfinished_req", "request_metadata_source": "attached_object.rid", "semantic_token_count": 0, "semantic_token_ids_preview": [], "semantic_token_source": null, "sglang_request_id": "9ebc9560bd924d128f72b8e8e5322ea0", "timestamp": "2026-07-08T22:28:50.272373Z", "timestamp_ns": 1783549730272388473, "transfer_log_profile": "full", "worker_cache_control_seen": false, "worker_priority_seen": false}
[SGLANG_TRANSFER_JSON] {"action": "insert", "cache_page_size": 64, "cache_prefix_len": 0, "event": "sglang.cache", "function": "insert", "request_context_function": "cache_unfinished_req", "request_metadata_source": "attached_object.rid", "semantic_token_count": 0, "semantic_token_ids_preview": [], "semantic_token_source": null, "sglang_request_id": "9ebc9560bd924d128f72b8e8e5322ea0", "timestamp": "2026-07-08T22:28:50.272373Z", "timestamp_ns": 1783549730272388473, "transfer_log_profile": "full", "worker_cache_control_seen": false, "worker_priority_seen": false}
[SGLANG_TRANSFER_JSON] {"action": "insert", "cache_new_prefix_len": 0, "cache_page_size": 64, "cache_prefix_len": 0, "event": "sglang.cache", "function": "insert", "request_context_function": "cache_unfinished_req", "request_metadata_source": "attached_object.rid", "semantic_context_function": "cache_unfinished_req", "semantic_token_count": 0, "semantic_token_ids_preview": [151644, 872, 198, 20841, 448, 6896, 25, 10402], "semantic_token_ids_sha256": "582803443087648e871d787968d9ccac01f126552930405fdc8ced9c4342a038", "semantic_token_preview_count": 8, "semantic_token_source": "cache_unfinished_req.req.origin_input_ids", "sglang_request_id": "9ebc9560bd924d128f72b8e8e5322ea0", "timestamp": "2026-07-08T22:28:50.272373Z", "timestamp_ns": 1783549730272388473, "transfer_log_profile": "full", "worker_cache_control_seen": false, "worker_priority_seen": false}
2026-07-08T22:28:50.274739Z  INFO scheduler_metrics_mixin.report_prefill_stats: Prefill batch, #new-seq: 1, #new-token: 64, #cached-token: 0, token usage: 0.00, #running-req: 0, #queue-req: 0, #pending-token: 0, cuda graph: True, input throughput (token/s): 0.23
2026-07-08T22:28:50.275896Z  INFO runtime_logging.emit_runtime_event: [RUNTIME_JSON] {"agent_hints":null,"agent_hints_keys":[],"agent_hints_source":"missing","cache_control":null,"cache_control_source":"missing","cache_control_ttl":null,"cache_control_type":null,"component":"worker.decode","event_type":"worker.decode.request_attached","external_request_id":"a7d0086e-9a5b-4940-8b98-0026e75182df","hint_probe_id":null,"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8","request_context":null,"runtime_context_id":"a7d0086e-9a5b-4940-8b98-0026e75182df","sglang_request_id":"9ebc9560bd924d128f72b8e8e5322ea0"}
[SGLANG_TRANSFER_JSON] {"action": "insert", "cache_new_prefix_len": 0, "cache_page_size": 64, "cache_prefix_len": 0, "event": "sglang.cache", "function": "insert", "request_context_function": "cache_finished_req", "request_metadata_source": "attached_object.rid", "semantic_context_function": "cache_unfinished_req", "semantic_token_count": 0, "semantic_token_ids_preview": [151644, 872, 198, 20841, 448, 6896, 25, 10402], "semantic_token_ids_sha256": "582803443087648e871d787968d9ccac01f126552930405fdc8ced9c4342a038", "semantic_token_preview_count": 8, "semantic_token_source": "cache_unfinished_req.req.origin_input_ids", "sglang_request_id": "9ebc9560bd924d128f72b8e8e5322ea0", "timestamp": "2026-07-08T22:28:50.272373Z", "timestamp_ns": 1783549730272388473, "transfer_log_profile": "full", "worker_cache_control_seen": false, "worker_priority_seen": false}
[SGLANG_TRANSFER_JSON] {"action": "insert", "cache_new_prefix_len": 0, "cache_page_size": 64, "cache_prefix_len": 0, "event": "sglang.cache", "function": "insert", "request_context_function": "cache_finished_req", "request_metadata_source": "attached_object.rid", "semantic_context_function": "cache_unfinished_req", "semantic_token_count": 0, "semantic_token_ids_preview": [151644, 872, 198, 20841, 448, 6896, 25, 10402], "semantic_token_ids_sha256": "582803443087648e871d787968d9ccac01f126552930405fdc8ced9c4342a038", "semantic_token_preview_count": 8, "semantic_token_source": "cache_unfinished_req.req.origin_input_ids", "sglang_request_id": "9ebc9560bd924d128f72b8e8e5322ea0", "timestamp": "2026-07-08T22:28:50.272373Z", "timestamp_ns": 1783549730272388473, "transfer_log_profile": "full", "worker_cache_control_seen": false, "worker_priority_seen": false}
2026-07-08T22:28:50.279528Z  INFO runtime_logging.emit_runtime_event: [RUNTIME_JSON] {"agent_hints":null,"agent_hints_keys":[],"agent_hints_source":"missing","cache_control":null,"cache_control_source":"missing","cache_control_ttl":null,"cache_control_type":null,"completion_usage":{"completion_tokens":2,"prompt_tokens":13,"prompt_tokens_details":null,"total_tokens":15},"component":"worker.decode","event_type":"worker.decode.request_completed","external_request_id":"a7d0086e-9a5b-4940-8b98-0026e75182df","finish_reason":"stop","hint_probe_id":null,"model":"Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8","request_context":null,"runtime_context_id":"a7d0086e-9a5b-4940-8b98-0026e75182df","serving_mode":"DisaggregationMode.AGGREGATED","sglang_request_id":"9ebc9560bd924d128f72b8e8e5322ea0","stop_reason":null}
2026-07-08T22:28:50.279781Z  INFO handle_payload: dynamo_runtime::pipeline::network::ingress::push_handler: request completed request_id=a7d0086e-9a5b-4940-8b98-0026e75182df request_id="a7d0086e-9a5b-4940-8b98-0026e75182df" component="backend" endpoint="generate" namespace="dynamo" instance_id=7587894972260893829
2026-07-08T22:30:17.098475Z  INFO handle_payload: dynamo_runtime::pipeline::network::ingress::push_handler: request received request_id=7c07e700-edde-49d8-bec1-a333947266a3 request_id="7c07e700-edde-49d8-bec1-a333947266a3" component="backend" endpoint="clear_kv_blocks" namespace="dynamo" instance_id=7587894972260893829
2026-07-08T22:30:17.100278Z  INFO scheduler.flush_cache: Cache flushed successfully!






Dynamo decode handler markers: {"attach_logged = False": true, "path": "/usr/local/lib/python3.12/dist-packages/dynamo/sglang/request_handlers/llm/decode_handler.py", "request: Dict[str, Any]": true, "worker.decode.request_attached": true}
/usr/local/lib/python3.12/dist-packages/torchao/quantization/quant_api.py:1731: SyntaxWarning: invalid escape sequence '\.'
  """Configuration class for applying different quantization configs to modules or parameters based on their fully qualified names (FQNs).
SGLang transfer markers: {"_sgl_log_transfer_event": true, "path": "/workspace/sglang_transfer_overlay/sglang/srt/mem_cache/memory_pool_host.py"}
========================================
(4/6) PRECISE ATTRIBUTION READY (the live running worker really has the instrumentation)
========================================
PASS: precise transfer attribution is ready
========================================
(5/6) MODEL READINESS GO (model registration and smoke test both passed)
========================================
========================================
(6/6) PRECISE EXPERIMENT GO (smoke test passed and requests are about to start)
========================================
Machine profile: gh200
Attribution mode: transfer
Smoke test: ok
Live attribution check: ok
Requests may now start.
Cooldown: 60s
Checking live KV cache flush endpoint before requests...
clear_kv_blocks did not fully invalidate runtime state: [{"flush_cache_status": "success", "kv_clear_event_status": "unavailable", "name": "dynamo/backend-instance-7587894972260893829", "response": {"flush_cache_status": "success", "http_worker_ipc": null, "kv_clear_event_publishers": 0, "kv_clear_event_status": "unavailable", "message": "", "rid": null, "status": "partial_success", "success": true}}]
Stopping threshold sweep because STOP_ON_PROBE_FAILURE=1
ojaiyeob@gracehopper:~/kv_cache_offloading$

2026-07-08T22:30:17.100806Z  INFO handle_payload: dynamo_runtime::pipeline::network::ingress::push_handler: request completed request_id=7c07e700-edde-49d8-bec1-a333947266a3 request_id="7c07e700-edde-49d8-bec1-a333947266a3" component="backend" endpoint="clear_kv_blocks" namespace="dynamo" instance_id=7587894972260893829
