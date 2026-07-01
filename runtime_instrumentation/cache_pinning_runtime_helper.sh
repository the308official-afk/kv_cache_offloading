#!/usr/bin/env bash

source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/cache_pinning_profile.sh"

cache_pinning_banner() {
  cat <<EOF
========================================
$1
========================================
EOF
}

cache_pinning_numbered_title() {
  printf '(%s/%s) %s\n' "$1" "$2" "$3"
}

cache_pinning_banner_numbered() {
  cache_pinning_banner "$(cache_pinning_numbered_title "$1" "$2" "$3")"
}

detect_cache_pinning_frontend_flag() {
  local root="$1"
  local frontend_args="${root}/lib/llm/src/kv_router/config.rs"
  local frontend_py="${root}/components/src/dynamo/frontend/frontend_args.py"
  local mode="${CACHE_PINNING_FRONTEND_FLAG_MODE:-auto}"
  local fixed_value="${CACHE_PINNING_FRONTEND_FLAG_VALUE:---enable-cache-control}"

  if [[ "${mode}" = "fixed" ]]; then
    printf '%s\n' "${fixed_value}"
    return 0
  fi

  if grep -q -- "--enable-agentic-cache-control" "${frontend_args}" 2>/dev/null; then
    printf '%s\n' "--enable-agentic-cache-control"
    return 0
  fi
  if grep -q -- "--enable-cache-control" "${frontend_py}" 2>/dev/null; then
    printf '%s\n' "--enable-cache-control"
    return 0
  fi
  return 1
}

require_cache_pinning_source_markers() {
  local dynamo_root="$1"
  local sglang_root="$2"
  grep -q "cache_control_ttl" "${dynamo_root}/lib/llm/src/preprocessor.rs" 2>/dev/null
  grep -q "spawn_pin_prefix" "${dynamo_root}/lib/llm/src/kv_router/push_router.rs" 2>/dev/null
  grep -q "cache_control_endpoint = runtime.endpoint(" "${dynamo_root}/components/src/dynamo/sglang/init_llm.py" 2>/dev/null
  grep -q "cache_control_endpoint.serve_endpoint(" "${dynamo_root}/components/src/dynamo/sglang/init_llm.py" 2>/dev/null
  grep -q "pin_prefix" "${sglang_root}/srt/mem_cache/hiradix_cache.py" 2>/dev/null
  grep -q "pin_expiry" "${sglang_root}/srt/mem_cache/hiradix_cache.py" 2>/dev/null
}

require_cache_pinning_instrumentation_markers() {
  local dynamo_root="$1"
  local sglang_root="$2"
  grep -q "router.cache_control_seen" "${dynamo_root}/lib/llm/src/kv_router/push_router.rs" 2>/dev/null
  grep -q "router.pin_prefix_spawned" "${dynamo_root}/lib/llm/src/kv_router/push_router.rs" 2>/dev/null
  grep -q "worker.pin_prefix_applied" "${sglang_root}/srt/mem_cache/hiradix_cache.py" 2>/dev/null
  grep -q "worker.pin_refreshed_cache_hit" "${sglang_root}/srt/mem_cache/hiradix_cache.py" 2>/dev/null
}

prepare_cache_pinning_sources() {
  local log_path="${1:-/dev/null}"
  ./runtime_instrumentation/fetch_cache_pinning_dynamo_source.sh | tee -a "${log_path}"
  ./runtime_instrumentation/fetch_cache_pinning_sglang_source.sh | tee -a "${log_path}"
  SOURCE_DIR="${CACHE_PINNING_DYNAMO_SOURCE_DIR}" \
    python3 ./runtime_instrumentation/repair_cache_pinning_dynamo_source.py | tee -a "${log_path}"
  SOURCE_DIR="${CACHE_PINNING_SGLANG_SOURCE_DIR}" \
    python3 ./runtime_instrumentation/repair_cache_pinning_sglang_source.py | tee -a "${log_path}"

  if ! require_cache_pinning_source_markers "${CACHE_PINNING_DYNAMO_SOURCE_DIR}" "${CACHE_PINNING_SGLANG_ROOT}"; then
    echo "Cache-pinning source markers were not found in the isolated PR stack." | tee -a "${log_path}" >&2
    return 1
  fi
  if ! require_cache_pinning_instrumentation_markers "${CACHE_PINNING_DYNAMO_SOURCE_DIR}" "${CACHE_PINNING_SGLANG_ROOT}"; then
    echo "Cache-pinning instrumentation markers were not found in the isolated PR stack." | tee -a "${log_path}" >&2
    return 1
  fi
}

ensure_cache_pinning_runtime_images() {
  local log_path="${1:-/dev/null}"
  local step_label="${2:-CACHE PINNING IMAGE READY (isolated cache-pinning images are there)}"
  local total_steps="${3:-6}"
  local step_number="${4:-1}"
  local need_build=0
  local -a build_reasons=()

  if [[ "${CACHE_PINNING_REBUILD_IMAGES:-0}" = "1" ]]; then
    need_build=1
    build_reasons+=("CACHE_PINNING_REBUILD_IMAGES=1")
  fi
  if ! docker image inspect "${CACHE_PINNING_FRONTEND_IMAGE}" >/dev/null 2>&1; then
    need_build=1
    build_reasons+=("frontend image missing")
  fi
  if ! docker image inspect "${CACHE_PINNING_WORKER_IMAGE}" >/dev/null 2>&1; then
    need_build=1
    build_reasons+=("worker image missing")
  fi

  if [[ "${need_build}" = "0" ]]; then
    echo "Reusing existing cache-pinning images; no isolated Dynamo rebuild needed for this run." | tee -a "${log_path}"
    echo "Frontend image: ${CACHE_PINNING_FRONTEND_IMAGE}" | tee -a "${log_path}"
    echo "Worker image: ${CACHE_PINNING_WORKER_IMAGE}" | tee -a "${log_path}"
    echo "frontend image ok" | tee -a "${log_path}"
    echo "worker image ok" | tee -a "${log_path}"
    cache_pinning_banner_numbered "${step_number}" "${total_steps}" "${step_label}" | tee -a "${log_path}"
    return 0
  fi

  if [[ "${AUTO_BUILD_CACHE_PINNING_IMAGES:-1}" != "1" ]]; then
    echo "Missing cache-pinning runtime images and auto-build is disabled." >&2
    return 1
  fi

  echo "Preparing isolated cache-pinning sources..." | tee -a "${log_path}"
  prepare_cache_pinning_sources "${log_path}"

  echo "Building isolated cache-pinning runtime images from the cache-pinning PR stack..." | tee -a "${log_path}"
  if [[ "${#build_reasons[@]}" -gt 0 ]]; then
    printf 'Build reason(s): %s\n' "${build_reasons[*]}" | tee -a "${log_path}"
  fi
  SOURCE_DIR="${CACHE_PINNING_DYNAMO_SOURCE_DIR}" \
  FRONTEND_IMAGE_TAG="${CACHE_PINNING_FRONTEND_IMAGE}" \
  WORKER_IMAGE_TAG="${CACHE_PINNING_WORKER_IMAGE}" \
  LEAN_FRONTEND=1 \
    ./runtime_instrumentation/build_cache_pinning_dynamo_images.sh | tee -a "${log_path}"

  docker image inspect "${CACHE_PINNING_FRONTEND_IMAGE}" >/dev/null 2>&1
  docker image inspect "${CACHE_PINNING_WORKER_IMAGE}" >/dev/null 2>&1
  echo "frontend image ok" | tee -a "${log_path}"
  echo "worker image ok" | tee -a "${log_path}"
  cache_pinning_banner_numbered "${step_number}" "${total_steps}" "${step_label}" | tee -a "${log_path}"
}
