#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source agentbench/model_config.sh

MODEL_LIST_FILE="${MODEL_LIST_FILE:-agentbench/model_lists/multi_model_batch.txt}"
DESIGN_SPACE_ID="${DESIGN_SPACE_ID:-design_space_$(date +%Y%m%d_%H%M%S)}"
START_INDEX="${START_INDEX:-0}"
END_INDEX="${END_INDEX:-2}"
HINT_PROFILES="${HINT_PROFILES:-baseline high-reuse}"
HINT_PROVIDER="${HINT_PROVIDER:-agentbench}"
LLM_STAGES="${LLM_STAGES:-prefill decode}"
LLM_OPERATIONS="${LLM_OPERATIONS:-attention_kv ffn_mlp}"
KV_TIER_MODES="${KV_TIER_MODES:-gpu_cpu}"
SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE:-full}"
SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING:-0}"
MEM_FRACTION_STATIC="${MEM_FRACTION_STATIC:-0.7}"
HICACHE_RATIO="${HICACHE_RATIO:-1}"
HICACHE_STORAGE_BACKEND="${HICACHE_STORAGE_BACKEND:-file}"
HICACHE_STORAGE_PREFETCH_POLICY="${HICACHE_STORAGE_PREFETCH_POLICY:-wait_complete}"
HICACHE_WRITE_POLICY="${HICACHE_WRITE_POLICY:-}"
HICACHE_EXTRA_ARGS="${HICACHE_EXTRA_ARGS:-}"
FILE_STORAGE_PATH="${FILE_STORAGE_PATH:-/hicache-storage}"
HOST_FILE_STORAGE_PATH="${HOST_FILE_STORAGE_PATH:-/mnt/docker-data/hicache_storage}"
STORAGE_MEDIA="${STORAGE_MEDIA:-unknown}"
STORAGE_CAPACITY_GB="${STORAGE_CAPACITY_GB:-}"
WORKER_BASE_ARGS="${WORKER_BASE_ARGS:---enable-cache-report --enable-priority-scheduling --radix-eviction-policy lru}"
WORKER_EXTRA_ARGS_SUFFIX="${WORKER_EXTRA_ARGS_SUFFIX:-}"
MODEL_SMOKE_RETRIES="${MODEL_SMOKE_RETRIES:-60}"
MODEL_SMOKE_DELAY_SECS="${MODEL_SMOKE_DELAY_SECS:-10}"
MODEL_COOLDOWN_SECS="${MODEL_COOLDOWN_SECS:-30}"
STOP_DYNAMO_WHEN_DONE="${STOP_DYNAMO_WHEN_DONE:-0}"
REQUIRE_PRECISE_KV="${REQUIRE_PRECISE_KV:-1}"
PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT:-1000}"
FRONTEND_IMAGE="${FRONTEND_IMAGE:-local/dynamo-frontend:runtime-json-logs}"
WORKER_IMAGE="${WORKER_IMAGE:-local/dynamo-sglang:runtime-json-logs}"
CLI_MODELS=("$@")

DESIGN_SPACE_DIR="experiments/reports/design_space/${DESIGN_SPACE_ID}"
DESIGN_SPACE_LOG="${DESIGN_SPACE_DIR}/design_space_progress.log"
DESIGN_SPACE_MATRIX="${DESIGN_SPACE_DIR}/design_space_matrix.csv"
DESIGN_SPACE_SUMMARY="${DESIGN_SPACE_DIR}/design_space_summary.md"
GLOBAL_MATRIX="experiments/reports/design_space_matrix.csv"
mkdir -p "${DESIGN_SPACE_DIR}"
DESIGN_SPACE_HEADER="design_space_id,model,hint_profile,hint_provider,start_index,end_index,task_count,llm_stage,llm_operation,stage_operation_source,kv_tier_mode,sglang_transfer_log_profile,gpu_hbm_gb,host_ram_gb,cpu_gpu_interconnect,mem_fraction_static,hicache_ratio,storage_backend,storage_prefetch_policy,file_storage_path,host_file_storage_path,storage_media,storage_capacity_gb,batch_id,completed_count,failed_count,avg_ttft_ms,avg_latency_ms,avg_cache_reuse_ratio,avg_cached_tokens,avg_recomputed_prefix_tokens,host_to_device_transfer_count,host_to_device_mb,device_to_host_transfer_count,device_to_host_mb,avg_transfer_cuda_sync_ms,direct_attribution_rate,patch_rate,avg_patch_bytes,progress_csv"

usage() {
  cat <<EOF
Usage:
  $0 [model ...]

Examples:
  START_INDEX=0 END_INDEX=2 HINT_PROFILES='baseline high-reuse' \\
    KV_TIER_MODES='gpu_only gpu_cpu gpu_cpu_storage' \\
    SGLANG_TRANSFER_LOG_PROFILE=full $0 \\
    Qwen/Qwen2.5-Coder-7B-Instruct Qwen/Qwen2.5-7B-Instruct

Model source priority:
  1. positional model arguments
  2. MODELS='model-a,model-b'
  3. MODEL_LIST_FILE, one model per line
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

safe_name() {
  echo "$1" | tr '/:.' '___' | tr -cs 'A-Za-z0-9_-' '_'
}

load_models() {
  if [[ "${#CLI_MODELS[@]}" -gt 0 ]]; then
    printf '%s\n' "${CLI_MODELS[@]}" | tr ',' '\n' | awk '{$1=$1}; NF && $1 !~ /^#/'
    return
  fi

  if [[ -n "${MODELS:-}" ]]; then
    printf '%s\n' "${MODELS}" | tr ',' '\n' | awk '{$1=$1}; NF && $1 !~ /^#/'
    return
  fi

  if [[ ! -f "${MODEL_LIST_FILE}" ]]; then
    cat >&2 <<EOF
Model list file not found:
  ${MODEL_LIST_FILE}

Create it with one model per line, pass MODELS='model-a,model-b', or pass
models directly as positional arguments.
EOF
    exit 1
  fi

  awk '{$1=$1}; NF && $1 !~ /^#/' "${MODEL_LIST_FILE}"
}

auto_gpu_hbm_gb() {
  if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | \
      head -1 | awk '{printf "%.0f", ($1 / 1024)}'
  fi
}

auto_host_ram_gb() {
  if [[ -r /proc/meminfo ]]; then
    awk '/MemTotal:/ {printf "%.0f", ($2 / 1024 / 1024)}' /proc/meminfo
  fi
}

auto_storage_capacity_gb() {
  local path="$1"
  if command -v df >/dev/null 2>&1 && [[ -n "${path}" ]]; then
    mkdir -p "${path}" 2>/dev/null || true
    df -Pk "${path}" 2>/dev/null | awk 'NR == 2 {printf "%.0f", ($2 / 1024 / 1024)}'
  fi
}

storage_host_path_for_mode() {
  local model_safe="$1"
  local kv_tier_mode="$2"
  echo "${HOST_FILE_STORAGE_PATH%/}/${DESIGN_SPACE_ID}/${model_safe}/${kv_tier_mode}"
}

worker_args_for_kv_tier_mode() {
  local kv_tier_mode="$1"
  local args="${WORKER_BASE_ARGS} --mem-fraction-static ${MEM_FRACTION_STATIC}"

  case "${kv_tier_mode}" in
    gpu_only)
      ;;
    gpu_cpu)
      args="${args} --enable-hierarchical-cache --hicache-ratio ${HICACHE_RATIO}"
      ;;
    gpu_cpu_storage)
      args="${args} --enable-hierarchical-cache --hicache-ratio ${HICACHE_RATIO}"
      if [[ -n "${HICACHE_WRITE_POLICY}" ]]; then
        args="${args} --hicache-write-policy ${HICACHE_WRITE_POLICY}"
      fi
      args="${args} --hicache-storage-backend ${HICACHE_STORAGE_BACKEND}"
      args="${args} --hicache-storage-prefetch-policy ${HICACHE_STORAGE_PREFETCH_POLICY}"
      args="${args} --file-storage-path ${FILE_STORAGE_PATH}"
      ;;
    *)
      echo "Unknown KV_TIER_MODE: ${kv_tier_mode}" >&2
      echo "Valid values: gpu_only gpu_cpu gpu_cpu_storage" >&2
      exit 2
      ;;
  esac

  if [[ -n "${HICACHE_EXTRA_ARGS}" ]]; then
    args="${args} ${HICACHE_EXTRA_ARGS}"
  fi
  if [[ -n "${WORKER_EXTRA_ARGS_SUFFIX}" ]]; then
    args="${args} ${WORKER_EXTRA_ARGS_SUFFIX}"
  fi

  echo "${args}"
}

resolve_sglang_root() {
  if [[ -n "${SGLANG_ROOT:-}" && -f "${SGLANG_ROOT}/__init__.py" ]]; then
    echo "${SGLANG_ROOT}"
    return
  fi
  if [[ -n "${WORKER_SGLANG_SOURCE_ROOT:-}" && -f "${WORKER_SGLANG_SOURCE_ROOT}/__init__.py" ]]; then
    echo "${WORKER_SGLANG_SOURCE_ROOT}"
    return
  fi
  if [[ -f "${PWD}/upstream/sglang/python/sglang/__init__.py" ]]; then
    echo "${PWD}/upstream/sglang/python/sglang"
    return
  fi
  if [[ -f "${PWD}/runtime_upstream/sglang/python/sglang/__init__.py" ]]; then
    echo "${PWD}/runtime_upstream/sglang/python/sglang"
    return
  fi
}

require_precise_kv_ready() {
  if [[ "${REQUIRE_PRECISE_KV}" != "1" ]]; then
    return 0
  fi

  if [[ -z "${RESOLVED_SGLANG_ROOT:-}" ]]; then
    cat >&2 <<EOF
Precise KV attribution requires patched SGLang source.

Set SGLANG_ROOT or WORKER_SGLANG_SOURCE_ROOT to the extracted/patched package,
for example:
  export SGLANG_ROOT="\$PWD/upstream/sglang/python/sglang"
EOF
    exit 1
  fi

  if ! grep -q "_sgl_log_transfer_event" "${RESOLVED_SGLANG_ROOT}/srt/mem_cache/memory_pool_host.py" 2>/dev/null; then
    cat >&2 <<EOF
SGLang source does not appear patched for transfer logging:
  ${RESOLVED_SGLANG_ROOT}

Run:
  python3 runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py --sglang-root "${RESOLVED_SGLANG_ROOT}"
EOF
    exit 1
  fi
}

init_matrix_file() {
  local path="$1"
  if [[ -f "${path}" && "$(head -n 1 "${path}")" != "${DESIGN_SPACE_HEADER}" ]]; then
    mv "${path}" "${path%.csv}_legacy_$(date +%Y%m%d_%H%M%S).csv"
  fi
  if [[ ! -f "${path}" ]]; then
    printf '%s\n' "${DESIGN_SPACE_HEADER}" > "${path}"
  fi
}

append_design_space_rows() {
  local model="$1"
  local hint_profile="$2"
  local kv_tier_mode="$3"
  local storage_backend="$4"
  local storage_prefetch_policy="$5"
  local file_storage_path="$6"
  local host_file_storage_path="$7"
  local storage_media="$8"
  local storage_capacity_gb="$9"
  local batch_id="${10}"
  local progress_csv="${11}"

  DESIGN_SPACE_ID_VALUE="${DESIGN_SPACE_ID}" \
  MODEL_VALUE="${model}" \
  HINT_PROFILE_VALUE="${hint_profile}" \
  HINT_PROVIDER_VALUE="${HINT_PROVIDER}" \
  START_INDEX_VALUE="${START_INDEX}" \
  END_INDEX_VALUE="${END_INDEX}" \
  TASK_COUNT_VALUE="${TASK_COUNT}" \
  LLM_STAGES_VALUE="${LLM_STAGES}" \
  LLM_OPERATIONS_VALUE="${LLM_OPERATIONS}" \
  KV_TIER_MODE_VALUE="${kv_tier_mode}" \
  SGLANG_TRANSFER_LOG_PROFILE_VALUE="${SGLANG_TRANSFER_LOG_PROFILE}" \
  GPU_HBM_GB_VALUE="${GPU_HBM_GB}" \
  HOST_RAM_GB_VALUE="${HOST_RAM_GB}" \
  CPU_GPU_INTERCONNECT_VALUE="${CPU_GPU_INTERCONNECT}" \
  MEM_FRACTION_STATIC_VALUE="${MEM_FRACTION_STATIC}" \
  HICACHE_RATIO_VALUE="${HICACHE_RATIO}" \
  STORAGE_BACKEND_VALUE="${storage_backend}" \
  STORAGE_PREFETCH_POLICY_VALUE="${storage_prefetch_policy}" \
  FILE_STORAGE_PATH_VALUE="${file_storage_path}" \
  HOST_FILE_STORAGE_PATH_VALUE="${host_file_storage_path}" \
  STORAGE_MEDIA_VALUE="${storage_media}" \
  STORAGE_CAPACITY_GB_VALUE="${storage_capacity_gb}" \
  BATCH_ID_VALUE="${batch_id}" \
  PROGRESS_CSV_VALUE="${progress_csv}" \
  DESIGN_SPACE_MATRIX="${DESIGN_SPACE_MATRIX}" \
  GLOBAL_MATRIX="${GLOBAL_MATRIX}" \
  python3 - <<'PY'
import csv
import os
from pathlib import Path

fields = [
    "design_space_id",
    "model",
    "hint_profile",
    "hint_provider",
    "start_index",
    "end_index",
    "task_count",
    "llm_stage",
    "llm_operation",
    "stage_operation_source",
    "kv_tier_mode",
    "sglang_transfer_log_profile",
    "gpu_hbm_gb",
    "host_ram_gb",
    "cpu_gpu_interconnect",
    "mem_fraction_static",
    "hicache_ratio",
    "storage_backend",
    "storage_prefetch_policy",
    "file_storage_path",
    "host_file_storage_path",
    "storage_media",
    "storage_capacity_gb",
    "batch_id",
    "completed_count",
    "failed_count",
    "avg_ttft_ms",
    "avg_latency_ms",
    "avg_cache_reuse_ratio",
    "avg_cached_tokens",
    "avg_recomputed_prefix_tokens",
    "host_to_device_transfer_count",
    "host_to_device_mb",
    "device_to_host_transfer_count",
    "device_to_host_mb",
    "avg_transfer_cuda_sync_ms",
    "direct_attribution_rate",
    "patch_rate",
    "avg_patch_bytes",
    "progress_csv",
]

def as_float(value):
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

def as_int(value):
    number = as_float(value)
    return int(number) if number is not None else 0

def truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}

def avg(values):
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else None

def fmt(value, places=3):
    if value is None:
        return ""
    if places == 0:
        return str(round(value))
    return f"{value:.{places}f}"

def load_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

progress_csv = Path(os.environ["PROGRESS_CSV_VALUE"])
progress_rows = load_csv(progress_csv)
run_ids = {row.get("run_id") for row in progress_rows if row.get("run_id")}
task_count = int(os.environ["TASK_COUNT_VALUE"])
completed_count = len(run_ids)
failed_count = max(task_count - completed_count, 0)

patch_values = [as_float(row.get("patch_bytes")) for row in progress_rows if row.get("patch_bytes") not in (None, "")]
patch_nonempty_count = sum(1 for row in progress_rows if truthy(row.get("patch_nonempty")))
patch_rate = patch_nonempty_count / completed_count if completed_count else None

phase_rows = [
    row for row in load_csv("experiments/reports/all_runs_phase_metrics.csv")
    if row.get("run_id") in run_ids
]
transfer_rows = [
    row for row in load_csv("experiments/reports/all_runs_kv_transfer_metrics.csv")
    if row.get("run_id") in run_ids
]

ttft_values = [as_float(row.get("ttft_ms")) for row in phase_rows]
latency_values = [as_float(row.get("latency_ms")) for row in phase_rows]
reuse_values = [as_float(row.get("cache_reuse_ratio")) for row in phase_rows]
cached_values = [as_float(row.get("cached_token_count")) for row in phase_rows]
recomputed_values = [as_float(row.get("recomputed_prefix_tokens")) for row in phase_rows]
attribution_values = [truthy(row.get("transfer_request_id_matched")) for row in phase_rows]
direct_attribution_rate = (
    sum(1 for value in attribution_values if value) / len(attribution_values)
    if attribution_values else None
)

host_to_device_count = 0
device_to_host_count = 0
host_to_device_mb = 0.0
device_to_host_mb = 0.0
transfer_sync_values = []
for row in transfer_rows:
    direction = row.get("direction")
    count = as_int(row.get("count"))
    mb = as_float(row.get("kv_num_mb_estimated")) or 0.0
    sync_ms = as_float(row.get("elapsed_ms_cuda_sync"))
    if sync_ms is not None:
        transfer_sync_values.append(sync_ms)
    if direction == "host_to_device":
        host_to_device_count += count
        host_to_device_mb += mb
    elif direction == "device_to_host":
        device_to_host_count += count
        device_to_host_mb += mb

base = {
    "design_space_id": os.environ["DESIGN_SPACE_ID_VALUE"],
    "model": os.environ["MODEL_VALUE"],
    "hint_profile": os.environ["HINT_PROFILE_VALUE"],
    "hint_provider": os.environ["HINT_PROVIDER_VALUE"],
    "start_index": os.environ["START_INDEX_VALUE"],
    "end_index": os.environ["END_INDEX_VALUE"],
    "task_count": task_count,
    "stage_operation_source": "metadata_only",
    "kv_tier_mode": os.environ["KV_TIER_MODE_VALUE"],
    "sglang_transfer_log_profile": os.environ["SGLANG_TRANSFER_LOG_PROFILE_VALUE"],
    "gpu_hbm_gb": os.environ["GPU_HBM_GB_VALUE"],
    "host_ram_gb": os.environ["HOST_RAM_GB_VALUE"],
    "cpu_gpu_interconnect": os.environ["CPU_GPU_INTERCONNECT_VALUE"],
    "mem_fraction_static": os.environ["MEM_FRACTION_STATIC_VALUE"],
    "hicache_ratio": os.environ["HICACHE_RATIO_VALUE"],
    "storage_backend": os.environ["STORAGE_BACKEND_VALUE"],
    "storage_prefetch_policy": os.environ["STORAGE_PREFETCH_POLICY_VALUE"],
    "file_storage_path": os.environ["FILE_STORAGE_PATH_VALUE"],
    "host_file_storage_path": os.environ["HOST_FILE_STORAGE_PATH_VALUE"],
    "storage_media": os.environ["STORAGE_MEDIA_VALUE"],
    "storage_capacity_gb": os.environ["STORAGE_CAPACITY_GB_VALUE"],
    "batch_id": os.environ["BATCH_ID_VALUE"],
    "completed_count": completed_count,
    "failed_count": failed_count,
    "avg_ttft_ms": fmt(avg(ttft_values), places=0),
    "avg_latency_ms": fmt(avg(latency_values), places=0),
    "avg_cache_reuse_ratio": fmt(avg(reuse_values), places=3),
    "avg_cached_tokens": fmt(avg(cached_values), places=0),
    "avg_recomputed_prefix_tokens": fmt(avg(recomputed_values), places=0),
    "host_to_device_transfer_count": host_to_device_count,
    "host_to_device_mb": fmt(host_to_device_mb, places=3),
    "device_to_host_transfer_count": device_to_host_count,
    "device_to_host_mb": fmt(device_to_host_mb, places=3),
    "avg_transfer_cuda_sync_ms": fmt(avg(transfer_sync_values), places=0),
    "direct_attribution_rate": fmt(direct_attribution_rate, places=3),
    "patch_rate": fmt(patch_rate, places=3),
    "avg_patch_bytes": fmt(avg(patch_values), places=0),
    "progress_csv": str(progress_csv),
}

stages = [item for item in os.environ["LLM_STAGES_VALUE"].split() if item]
operations = [item for item in os.environ["LLM_OPERATIONS_VALUE"].split() if item]
rows = []
for stage in stages:
    for operation in operations:
        row = dict(base)
        row["llm_stage"] = stage
        row["llm_operation"] = operation
        rows.append(row)

for path_env in ("DESIGN_SPACE_MATRIX", "GLOBAL_MATRIX"):
    path = Path(os.environ[path_env])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
PY
}

write_summary() {
  DESIGN_SPACE_MATRIX="${DESIGN_SPACE_MATRIX}" \
  DESIGN_SPACE_SUMMARY="${DESIGN_SPACE_SUMMARY}" \
  DESIGN_SPACE_ID="${DESIGN_SPACE_ID}" \
  SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
  KV_TIER_MODES="${KV_TIER_MODES}" \
  GPU_HBM_GB="${GPU_HBM_GB}" \
  HOST_RAM_GB="${HOST_RAM_GB}" \
  CPU_GPU_INTERCONNECT="${CPU_GPU_INTERCONNECT}" \
  MEM_FRACTION_STATIC="${MEM_FRACTION_STATIC}" \
  HICACHE_RATIO="${HICACHE_RATIO}" \
  HICACHE_STORAGE_BACKEND="${HICACHE_STORAGE_BACKEND}" \
  HICACHE_STORAGE_PREFETCH_POLICY="${HICACHE_STORAGE_PREFETCH_POLICY}" \
  FILE_STORAGE_PATH="${FILE_STORAGE_PATH}" \
  HOST_FILE_STORAGE_PATH="${HOST_FILE_STORAGE_PATH}" \
  STORAGE_MEDIA="${STORAGE_MEDIA}" \
  STORAGE_CAPACITY_GB="${STORAGE_CAPACITY_GB}" \
  DESIGN_SPACE_LOG="${DESIGN_SPACE_LOG}" \
  python3 - <<'PY'
import csv
import os
from pathlib import Path

matrix = Path(os.environ["DESIGN_SPACE_MATRIX"])
summary = Path(os.environ["DESIGN_SPACE_SUMMARY"])
rows = list(csv.DictReader(matrix.open(encoding="utf-8"))) if matrix.exists() else []
cells = len(rows)
batches = sorted({row.get("batch_id", "") for row in rows if row.get("batch_id")})
models = sorted({row.get("model", "") for row in rows if row.get("model")})
profiles = sorted({row.get("hint_profile", "") for row in rows if row.get("hint_profile")})
stages = sorted({row.get("llm_stage", "") for row in rows if row.get("llm_stage")})
operations = sorted({row.get("llm_operation", "") for row in rows if row.get("llm_operation")})
kv_tiers = sorted({row.get("kv_tier_mode", "") for row in rows if row.get("kv_tier_mode")})
completed = sum(int(float(row.get("completed_count") or 0)) for row in rows)
failed = sum(int(float(row.get("failed_count") or 0)) for row in rows)

lines = [
    f"# Design Space Summary: {os.environ['DESIGN_SPACE_ID']}",
    "",
    "## Scope",
    "",
    f"- Models: {', '.join(models) if models else 'none'}",
    f"- Hint profiles: {', '.join(profiles) if profiles else 'none'}",
    f"- LLM stages: {', '.join(stages) if stages else 'none'}",
    f"- LLM operations: {', '.join(operations) if operations else 'none'}",
    f"- KV tier modes: {', '.join(kv_tiers) if kv_tiers else os.environ['KV_TIER_MODES']}",
    f"- SGLang transfer log profile: {os.environ['SGLANG_TRANSFER_LOG_PROFILE']}",
    "",
    "## Hardware / Cache Metadata",
    "",
    f"- GPU HBM GB: {os.environ['GPU_HBM_GB']}",
    f"- Host RAM GB: {os.environ['HOST_RAM_GB']}",
    f"- CPU-GPU interconnect: {os.environ['CPU_GPU_INTERCONNECT']}",
    f"- mem_fraction_static: {os.environ['MEM_FRACTION_STATIC']}",
    f"- hicache_ratio: {os.environ['HICACHE_RATIO']}",
    f"- storage backend: {os.environ['HICACHE_STORAGE_BACKEND']}",
    f"- storage prefetch policy: {os.environ['HICACHE_STORAGE_PREFETCH_POLICY']}",
    f"- container file storage path: {os.environ['FILE_STORAGE_PATH']}",
    f"- host file storage base path: {os.environ['HOST_FILE_STORAGE_PATH']}",
    f"- storage media: {os.environ['STORAGE_MEDIA']}",
    f"- storage capacity GB: {os.environ['STORAGE_CAPACITY_GB'] or 'unknown'}",
    "",
    "## Results",
    "",
    f"- Matrix rows: {cells}",
    f"- Batches: {len(batches)}",
    f"- Completed run references across rows: {completed}",
    f"- Failed run references across rows: {failed}",
    "",
    "## Files",
    "",
    f"- Matrix: `{matrix}`",
    f"- Progress log: `{os.environ['DESIGN_SPACE_LOG']}`",
    "",
    "Note: `llm_stage` and `llm_operation` are metadata/reporting dimensions in this first implementation.",
    "The existing AgentBench report builder still owns the detailed run, phase, request, KV, and prompt-evolution reports.",
    "",
]
summary.write_text("\n".join(lines), encoding="utf-8")
PY
}

smoke_test_model() {
  local model="$1"
  local smoke_log="$2"
  local frontend_port="${DYNAMO_FRONTEND_PORT:-8000}"
  local chat_url="http://127.0.0.1:${frontend_port}/v1/chat/completions"
  local models_url="http://127.0.0.1:${frontend_port}/v1/models"
  local registered_models
  local model_listed
  local payload

  for ((attempt=1; attempt<=MODEL_SMOKE_RETRIES; attempt++)); do
    echo "Smoke test ${attempt}/${MODEL_SMOKE_RETRIES} for ${model}" | tee -a "${DESIGN_SPACE_LOG}"
    registered_models="$(curl -fsS "${models_url}" 2>/dev/null || true)"
    {
      echo
      echo "Smoke test attempt ${attempt} for ${model}"
      echo "Registered models before chat:"
      echo "${registered_models:-<unavailable>}"
    } >> "${smoke_log}" 2>&1

    model_listed="$(
      REGISTERED_MODELS="${registered_models}" \
      EXPECTED_MODEL="${model}" \
      python3 - <<'PY'
import json
import os

try:
    payload = json.loads(os.environ.get("REGISTERED_MODELS", "") or "{}")
except json.JSONDecodeError:
    print("0")
    raise SystemExit

expected = os.environ["EXPECTED_MODEL"]
for item in payload.get("data", []):
    if item.get("id") == expected:
        print("1")
        break
else:
    print("0")
PY
    )"

    if [[ "${model_listed}" != "1" ]]; then
      echo "Model is not listed yet; waiting ${MODEL_SMOKE_DELAY_SECS}s." >> "${smoke_log}"
      sleep "${MODEL_SMOKE_DELAY_SECS}"
      continue
    fi

    payload="$(python3 -c 'import json, sys; print(json.dumps({"model": sys.argv[1], "messages": [{"role": "user", "content": "Reply with exactly: OK"}], "max_tokens": 10}))' "${model}")"
    if curl -fsS "${chat_url}" \
      -H "Content-Type: application/json" \
      -d "${payload}" >> "${smoke_log}" 2>&1; then
      echo "Smoke test passed for ${model}" | tee -a "${DESIGN_SPACE_LOG}"
      return 0
    fi
    {
      echo
      echo "Smoke test attempt ${attempt} failed for ${model}"
      echo "URL: ${chat_url}"
      echo "Expected model: ${model}"
      echo "Waiting ${MODEL_SMOKE_DELAY_SECS}s before retry."
      echo
    } >> "${smoke_log}" 2>&1
    sleep "${MODEL_SMOKE_DELAY_SECS}"
  done

  echo "Smoke test failed for ${model}. See ${smoke_log}" | tee -a "${DESIGN_SPACE_LOG}" >&2
  return 1
}

MODELS_TO_RUN=()
while IFS= read -r MODEL_LINE; do
  MODELS_TO_RUN+=("${MODEL_LINE}")
done < <(load_models)
if [[ "${#MODELS_TO_RUN[@]}" -eq 0 ]]; then
  echo "No models to run." >&2
  exit 1
fi

RESOLVED_SGLANG_ROOT="$(resolve_sglang_root || true)"
require_precise_kv_ready

GPU_HBM_GB="${GPU_HBM_GB:-$(auto_gpu_hbm_gb || true)}"
HOST_RAM_GB="${HOST_RAM_GB:-$(auto_host_ram_gb || true)}"
STORAGE_CAPACITY_GB="${STORAGE_CAPACITY_GB:-$(auto_storage_capacity_gb "${HOST_FILE_STORAGE_PATH}" || true)}"
CPU_GPU_INTERCONNECT="${CPU_GPU_INTERCONNECT:-unknown}"
GPU_HBM_GB="${GPU_HBM_GB:-unknown}"
HOST_RAM_GB="${HOST_RAM_GB:-unknown}"
STORAGE_CAPACITY_GB="${STORAGE_CAPACITY_GB:-unknown}"

TASK_COUNT=$((END_INDEX - START_INDEX + 1))
init_matrix_file "${DESIGN_SPACE_MATRIX}"
init_matrix_file "${GLOBAL_MATRIX}"

{
  echo "Design space ID: ${DESIGN_SPACE_ID}"
  echo "Models: ${#MODELS_TO_RUN[@]}"
  printf '  %s\n' "${MODELS_TO_RUN[@]}"
  echo "Task range: ${START_INDEX}-${END_INDEX}"
  echo "Hint profiles: ${HINT_PROFILES}"
  echo "Hint provider: ${HINT_PROVIDER}"
  echo "LLM stages: ${LLM_STAGES}"
  echo "LLM operations: ${LLM_OPERATIONS}"
  echo "KV tier modes: ${KV_TIER_MODES}"
  echo "SGLang transfer log profile: ${SGLANG_TRANSFER_LOG_PROFILE}"
  echo "SGLang root: ${RESOLVED_SGLANG_ROOT:-<unset>}"
  echo "GPU HBM GB: ${GPU_HBM_GB}"
  echo "Host RAM GB: ${HOST_RAM_GB}"
  echo "CPU-GPU interconnect: ${CPU_GPU_INTERCONNECT}"
  echo "mem_fraction_static: ${MEM_FRACTION_STATIC}"
  echo "hicache_ratio: ${HICACHE_RATIO}"
  echo "storage backend: ${HICACHE_STORAGE_BACKEND}"
  echo "storage prefetch policy: ${HICACHE_STORAGE_PREFETCH_POLICY}"
  echo "container file storage path: ${FILE_STORAGE_PATH}"
  echo "host file storage base path: ${HOST_FILE_STORAGE_PATH}"
  echo "storage media: ${STORAGE_MEDIA}"
  echo "storage capacity GB: ${STORAGE_CAPACITY_GB}"
  echo "Output dir: ${DESIGN_SPACE_DIR}"
  echo
} | tee -a "${DESIGN_SPACE_LOG}"

for MODEL_NAME in "${MODELS_TO_RUN[@]}"; do
  MODEL_SAFE_NAME="$(safe_name "${MODEL_NAME}")"

  for KV_TIER_MODE in ${KV_TIER_MODES}; do
    KV_TIER_SAFE_NAME="$(safe_name "${KV_TIER_MODE}")"
    CURRENT_WORKER_EXTRA_ARGS="$(worker_args_for_kv_tier_mode "${KV_TIER_MODE}")"
    CURRENT_STORAGE_BACKEND=""
    CURRENT_STORAGE_PREFETCH_POLICY=""
    CURRENT_FILE_STORAGE_PATH=""
    CURRENT_HOST_FILE_STORAGE_PATH=""
    CURRENT_STORAGE_MEDIA=""
    CURRENT_STORAGE_CAPACITY_GB=""
    SMOKE_LOG="${DESIGN_SPACE_DIR}/${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_smoke_test.log"

    if [[ "${KV_TIER_MODE}" = "gpu_cpu_storage" ]]; then
      CURRENT_STORAGE_BACKEND="${HICACHE_STORAGE_BACKEND}"
      CURRENT_STORAGE_PREFETCH_POLICY="${HICACHE_STORAGE_PREFETCH_POLICY}"
      CURRENT_FILE_STORAGE_PATH="${FILE_STORAGE_PATH}"
      CURRENT_HOST_FILE_STORAGE_PATH="$(storage_host_path_for_mode "${MODEL_SAFE_NAME}" "${KV_TIER_MODE}")"
      CURRENT_STORAGE_MEDIA="${STORAGE_MEDIA}"
      CURRENT_STORAGE_CAPACITY_GB="${STORAGE_CAPACITY_GB}"
      mkdir -p "${CURRENT_HOST_FILE_STORAGE_PATH}" 2>/dev/null || true
    fi

    {
      echo "===== Model: ${MODEL_NAME} | KV tier: ${KV_TIER_MODE} ====="
      echo "Worker args: ${CURRENT_WORKER_EXTRA_ARGS}"
      if [[ "${KV_TIER_MODE}" = "gpu_cpu_storage" ]]; then
        echo "Storage backend: ${CURRENT_STORAGE_BACKEND}"
        echo "Storage prefetch policy: ${CURRENT_STORAGE_PREFETCH_POLICY}"
        echo "Container file storage path: ${CURRENT_FILE_STORAGE_PATH}"
        echo "Host file storage path: ${CURRENT_HOST_FILE_STORAGE_PATH}"
      fi
      echo "Stopping Dynamo..."
    } | tee -a "${DESIGN_SPACE_LOG}"

    ./run_dynamo_single_host.sh stop >> "${DESIGN_SPACE_LOG}" 2>&1 || true

    echo "Starting Dynamo for ${MODEL_NAME} with KV tier ${KV_TIER_MODE}..." | tee -a "${DESIGN_SPACE_LOG}"
    DYNAMO_MODEL_PATH="${MODEL_NAME}" \
    DYNAMO_SERVED_MODEL_NAME="${MODEL_NAME}" \
    WORKER_EXTRA_ARGS="${CURRENT_WORKER_EXTRA_ARGS}" \
    WORKER_SGLANG_DEV_MODE=1 \
    WORKER_SGLANG_SOURCE_ROOT="${RESOLVED_SGLANG_ROOT}" \
    HICACHE_STORAGE_HOST_PATH="${CURRENT_HOST_FILE_STORAGE_PATH}" \
    HICACHE_STORAGE_CONTAINER_PATH="${CURRENT_FILE_STORAGE_PATH}" \
    SGLANG_TRANSFER_LOG=1 \
    SGLANG_TRANSFER_LOG_PROFILE="${SGLANG_TRANSFER_LOG_PROFILE}" \
    SGLANG_TRANSFER_LOG_OVERHEAD_TIMING="${SGLANG_TRANSFER_LOG_OVERHEAD_TIMING}" \
    DYN_RUNTIME_JSON_LOGS=1 \
    DYN_TOOL_CALL_PARSER=hermes \
    FRONTEND_IMAGE="${FRONTEND_IMAGE}" \
    WORKER_IMAGE="${WORKER_IMAGE}" \
    ./run_dynamo_single_host.sh start >> "${DESIGN_SPACE_LOG}" 2>&1

    smoke_test_model "${MODEL_NAME}" "${SMOKE_LOG}"

    if [[ "${MODEL_COOLDOWN_SECS}" -gt 0 ]]; then
      echo "Cooldown: ${MODEL_COOLDOWN_SECS}s" | tee -a "${DESIGN_SPACE_LOG}"
      sleep "${MODEL_COOLDOWN_SECS}"
    fi

    for HINT_PROFILE in ${HINT_PROFILES}; do
      HINT_SAFE_NAME="$(safe_name "${HINT_PROFILE}")"
      BATCH_ID="${DESIGN_SPACE_ID}_${MODEL_SAFE_NAME}_${KV_TIER_SAFE_NAME}_${HINT_SAFE_NAME}"
      BATCH_DIR="experiments/reports/batches/${BATCH_ID}"

      echo "Running batch: model=${MODEL_NAME} kv_tier=${KV_TIER_MODE} hint_profile=${HINT_PROFILE}" | tee -a "${DESIGN_SPACE_LOG}"
      START_INDEX="${START_INDEX}" \
      END_INDEX="${END_INDEX}" \
      HINT_PROFILE="${HINT_PROFILE}" \
      HINT_PROVIDER="${HINT_PROVIDER}" \
      MODEL="${MODEL_NAME}" \
      MODEL_NAME="${MODEL_NAME}" \
      BATCH_ID="${BATCH_ID}" \
      PROMPT_EVOLUTION_VALUE_CHAR_LIMIT="${PROMPT_EVOLUTION_VALUE_CHAR_LIMIT}" \
      ./agentbench/run_swebench_batch_single_host.sh 2>&1 | tee -a "${DESIGN_SPACE_LOG}"

      append_design_space_rows \
        "${MODEL_NAME}" \
        "${HINT_PROFILE}" \
        "${KV_TIER_MODE}" \
        "${CURRENT_STORAGE_BACKEND}" \
        "${CURRENT_STORAGE_PREFETCH_POLICY}" \
        "${CURRENT_FILE_STORAGE_PATH}" \
        "${CURRENT_HOST_FILE_STORAGE_PATH}" \
        "${CURRENT_STORAGE_MEDIA}" \
        "${CURRENT_STORAGE_CAPACITY_GB}" \
        "${BATCH_ID}" \
        "${BATCH_DIR}/progress_overview.csv"

      write_summary
      echo "Updated matrix: ${DESIGN_SPACE_MATRIX}" | tee -a "${DESIGN_SPACE_LOG}"
      echo
    done
  done
done

if [[ "${STOP_DYNAMO_WHEN_DONE}" = "1" ]]; then
  echo "Stopping Dynamo after design-space run..." | tee -a "${DESIGN_SPACE_LOG}"
  ./run_dynamo_single_host.sh stop >> "${DESIGN_SPACE_LOG}" 2>&1 || true
fi

write_summary

{
  echo "Design-space run finished."
  echo "Matrix: ${DESIGN_SPACE_MATRIX}"
  echo "Summary: ${DESIGN_SPACE_SUMMARY}"
  echo "Log: ${DESIGN_SPACE_LOG}"
  echo "Global matrix: ${GLOBAL_MATRIX}"
} | tee -a "${DESIGN_SPACE_LOG}"
