cd ~/kv_cache_offloading

DYNAMO_MACHINE_PROFILE=gh200 \
KV_RETENTION_MODE=sweep \
KV_RETENTION_RESET_MODE=restart \
STOP_ON_PROBE_FAILURE=1 \
DISTRACTOR_COUNTS="25" \
PROTECTED_INPUT_LEN=400 \
DISTRACTOR_INPUT_LEN=400 \
PROTECTED_HINT_PROFILES="high-priority" \
./agentbench/run_kv_retention_microbenchmark_single_host.sh \
  Qwen/Qwen2.5-Coder-7B-Instruct
