#!/usr/bin/env bash

# Source this file from experiment wrappers that need patched SGLang overlays
# for precise attribution.
REPO_ROOT_FOR_PRECISE_SGLANG_HELPER="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SGLANG_SOURCE_PROFILE_SCRIPT="${REPO_ROOT_FOR_PRECISE_SGLANG_HELPER}/runtime_instrumentation/sglang_source_profile.sh"
if [[ -f "${SGLANG_SOURCE_PROFILE_SCRIPT}" ]]; then
  # shellcheck disable=SC1090
  source "${SGLANG_SOURCE_PROFILE_SCRIPT}"
fi

choose_precise_sglang_python() {
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    printf '%s\n' "${PYTHON_BIN}"
    return
  fi
  if command -v python3.11 >/dev/null 2>&1; then
    printf '%s\n' "python3.11"
    return
  fi
  printf '%s\n' "python3"
}

resolve_precise_sglang_root() {
  if [[ -n "${SGLANG_ROOT:-}" && -f "${SGLANG_ROOT}/__init__.py" ]]; then
    printf '%s\n' "${SGLANG_ROOT}"
    return
  fi
  if [[ -n "${WORKER_SGLANG_SOURCE_ROOT:-}" && -f "${WORKER_SGLANG_SOURCE_ROOT}/__init__.py" ]]; then
    printf '%s\n' "${WORKER_SGLANG_SOURCE_ROOT}"
    return
  fi
  if [[ -f "${PWD}/upstream/sglang/python/sglang/__init__.py" ]]; then
    printf '%s\n' "${PWD}/upstream/sglang/python/sglang"
    return
  fi
  if [[ -f "${PWD}/runtime_upstream/sglang/python/sglang/__init__.py" ]]; then
    printf '%s\n' "${PWD}/runtime_upstream/sglang/python/sglang"
    return
  fi
}

read_precise_sglang_source_image() {
  local root="$1"
  local source_file
  source_file="$(cd "${root}/../../" 2>/dev/null && pwd)/SOURCE_IMAGE.txt"
  if [[ -f "${source_file}" ]]; then
    grep '^image=' "${source_file}" | head -1 | cut -d= -f2-
  fi
}

_precise_sglang_log() {
  local message="$1"
  local log_file="${2:-}"
  if [[ -n "${log_file}" ]]; then
    printf '%s\n' "${message}" | tee -a "${log_file}"
  else
    printf '%s\n' "${message}" >&2
  fi
}

precise_banner() {
  local title="$1"
  local log_file="${2:-}"
  _precise_sglang_log "========================================" "${log_file}"
  _precise_sglang_log "${title}" "${log_file}"
  _precise_sglang_log "========================================" "${log_file}"
}

precise_numbered_title() {
  local step="$1"
  local total="$2"
  local title="$3"
  printf '(%s/%s) %s\n' "${step}" "${total}" "${title}"
}

precise_banner_numbered() {
  local step="$1"
  local total="$2"
  local title="$3"
  local log_file="${4:-}"
  precise_banner "$(precise_numbered_title "${step}" "${total}" "${title}")" "${log_file}"
}

_precise_sglang_run() {
  local log_file="$1"
  shift
  if [[ -n "${log_file}" ]]; then
    "$@" >> "${log_file}" 2>&1
  else
    "$@" >&2
  fi
}

_precise_sglang_require_markers() {
  local root="$1"
  local require_mode="${2:-transfer}"
  case "${require_mode}" in
    transfer)
      grep -q "_sgl_log_transfer_event" "${root}/srt/mem_cache/memory_pool_host.py" 2>/dev/null
      ;;
    priority)
      rg -q "_sgl_log_priority_event|priority_hint_seen|scheduler_priority_applied" \
        "${root}/srt/managers" \
        "${root}/srt/mem_cache" 2>/dev/null
      ;;
    both)
      _precise_sglang_require_markers "${root}" transfer && \
      _precise_sglang_require_markers "${root}" priority
      ;;
    specprefill)
      _precise_sglang_require_markers "${root}" transfer
      ;;
    *)
      echo "Unknown precise SGLang marker mode: ${require_mode}" >&2
      return 2
      ;;
  esac
}

resolve_precise_dynamo_root() {
  if [[ -n "${SOURCE_DIR:-}" && -f "${SOURCE_DIR}/Cargo.toml" ]]; then
    printf '%s\n' "${SOURCE_DIR}"
    return
  fi
  if [[ -f "${PWD}/upstream/dynamo/Cargo.toml" ]]; then
    printf '%s\n' "${PWD}/upstream/dynamo"
    return
  fi
}

_precise_dynamo_require_markers() {
  local root="$1"
  local require_mode="${2:-runtime}"
  case "${require_mode}" in
    runtime)
      grep -q "agent_hint_log_fields" "${root}/components/src/dynamo/common/runtime_logging.py" 2>/dev/null && \
      grep -q "worker.decode.request_attached" "${root}/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py" 2>/dev/null && \
      grep -q "worker.decode.request_completed" "${root}/components/src/dynamo/sglang/request_handlers/llm/decode_handler.py" 2>/dev/null && \
      grep -q "worker.prefill.request_attached" "${root}/components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py" 2>/dev/null && \
      grep -q "worker.prefill.request_completed" "${root}/components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py" 2>/dev/null && \
      grep -q "cache_control_source" "${root}/lib/llm/src/preprocessor.rs" 2>/dev/null && \
      grep -q "clear_kv_blocks_endpoint = runtime.endpoint(" "${root}/components/src/dynamo/sglang/init_llm.py" 2>/dev/null && \
      grep -q "clear_kv_blocks_endpoint.serve_endpoint(" "${root}/components/src/dynamo/sglang/init_llm.py" 2>/dev/null && \
      grep -q "async def clear_kv_blocks" "${root}/components/src/dynamo/sglang/request_handlers/handler_base.py" 2>/dev/null && \
      grep -q "flush_cache" "${root}/components/src/dynamo/sglang/request_handlers/handler_base.py" 2>/dev/null && \
      grep -q "register_engine_route(\"clear_kv_blocks\"" "${root}/components/src/dynamo/sglang/request_handlers/handler_base.py" 2>/dev/null
      ;;
    specprefill)
      grep -q "worker.spec_prefill.wrap_checked" "${root}/lib/llm/src/preprocessor/speculative_prefill.rs" 2>/dev/null && \
      grep -q "worker.spec_prefill.prefill_sent" "${root}/lib/llm/src/preprocessor/speculative_prefill.rs" 2>/dev/null && \
      grep -q "worker.spec_prefill.prefill_completed" "${root}/lib/llm/src/preprocessor/speculative_prefill.rs" 2>/dev/null
      ;;
    *)
      echo "Unknown precise Dynamo marker mode: ${require_mode}" >&2
      return 2
      ;;
  esac
}

precise_runtime_stamp_path() {
  local machine_profile="${1:-${DYNAMO_MACHINE_PROFILE:-default}}"
  printf '%s\n' "${REPO_ROOT_FOR_PRECISE_SGLANG_HELPER}/runtime_instrumentation/.precise_runtime_${machine_profile}.sha256"
}

precise_dynamo_source_signature() {
  local root="$1"
  local files=(
    "components/src/dynamo/common/runtime_logging.py"
    "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py"
    "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py"
    "lib/llm/src/preprocessor.rs"
    "lib/llm/src/protocols/openai/nvext.rs"
    "lib/llm/src/preprocessor/speculative_prefill.rs"
    "components/src/dynamo/sglang/init_llm.py"
    "components/src/dynamo/sglang/request_handlers/handler_base.py"
  )
  (
    cd "${root}"
    sha256sum "${files[@]}"
  ) | sha256sum | awk '{print $1}'
}

_precise_sglang_warn_missing_priority_markers() {
  local root="$1"
  local log_file="${2:-}"
  _precise_sglang_log "WARNING: priority-path markers were not found in extracted SGLang source." "${log_file}"
  _precise_sglang_log "WARNING: continuing with precise runtime/transfer attribution, but SGLang priority-path proof may be unavailable for this run." "${log_file}"
  _precise_sglang_log "WARNING: source root: ${root}" "${log_file}"
}

resolve_precise_sglang_source_image() {
  if [[ -n "${SGLANG_IMAGE:-}" ]]; then
    printf '%s\n' "${SGLANG_IMAGE}"
    return
  fi
  if [[ -n "${WORKER_IMAGE:-}" ]] && command -v docker >/dev/null 2>&1; then
    if docker image inspect "${WORKER_IMAGE}" >/dev/null 2>&1; then
      printf '%s\n' "${WORKER_IMAGE}"
      return
    fi
  fi
  if [[ -n "${SGLANG_SOURCE_IMAGE:-}" ]]; then
    printf '%s\n' "${SGLANG_SOURCE_IMAGE}"
    return
  fi
  if [[ -n "${SGLANG_PINNED_SOURCE_IMAGE:-}" ]]; then
    printf '%s\n' "${SGLANG_PINNED_SOURCE_IMAGE}"
    return
  fi
  if [[ -n "${WORKER_IMAGE:-}" ]]; then
    printf '%s\n' "${WORKER_IMAGE}"
    return
  fi
  printf '%s\n' "lmsysorg/sglang:v0.5.11-cu129-runtime"
}

prepare_precise_sglang_for_run() {
  local reason="${1:-precise attribution}"
  local log_file="${2:-}"
  local require_mode="${3:-transfer}"
  local py_bin="${PYTHON_BIN:-$(choose_precise_sglang_python)}"
  local resolved_root
  local desired_image=""

  desired_image="$(resolve_precise_sglang_source_image)"
  resolved_root="$(resolve_precise_sglang_root || true)"
  if [[ -n "${resolved_root}" ]]; then
    _precise_sglang_log "Reusing extracted SGLang source root: ${resolved_root}" "${log_file}"
    local existing_image=""
    existing_image="$(read_precise_sglang_source_image "${resolved_root}" || true)"
    if [[ -n "${existing_image}" && -n "${desired_image}" && "${existing_image}" != "${desired_image}" ]]; then
      _precise_sglang_log "Existing extracted source image does not match desired image." "${log_file}"
      _precise_sglang_log "Existing: ${existing_image}" "${log_file}"
      _precise_sglang_log "Desired:  ${desired_image}" "${log_file}"
      _precise_sglang_log "Refreshing extracted SGLang source from desired image..." "${log_file}"
      rm -rf "$(cd "${resolved_root}/../../" && pwd)"
      resolved_root=""
    fi
  fi

  if [[ -z "${resolved_root}" ]]; then
    _precise_sglang_log "Extracting SGLang source for ${reason}..." "${log_file}"
    _precise_sglang_log "Using pinned/selected SGLang source image: ${desired_image}" "${log_file}"
    _precise_sglang_run "${log_file}" env "SGLANG_IMAGE=${desired_image}" \
      ./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
    resolved_root="$(resolve_precise_sglang_root || true)"
  fi

  if [[ -z "${resolved_root}" ]]; then
    cat >&2 <<EOF
Could not resolve extracted SGLang source for ${reason}.

Expected one of:
  ${PWD}/upstream/sglang/python/sglang
  ${PWD}/runtime_upstream/sglang/python/sglang
EOF
    return 1
  fi

  _precise_sglang_log "Refreshing SGLang transfer logging patch for ${reason}..." "${log_file}"
  _precise_sglang_run "${log_file}" "${py_bin}" \
    runtime_instrumentation/sglang_transfer_logging/patch_sglang_transfer_logging.py \
    --sglang-root "${resolved_root}"

  if ! _precise_sglang_require_markers "${resolved_root}" "${require_mode}"; then
    if [[ "${require_mode}" = "priority" ]]; then
      if ! _precise_sglang_require_markers "${resolved_root}" "transfer"; then
        cat >&2 <<EOF
SGLang source does not appear patched for ${reason}:
  ${resolved_root}
Required marker set: ${require_mode}
EOF
        return 1
      fi
      _precise_sglang_warn_missing_priority_markers "${resolved_root}" "${log_file}"
      PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT=0
      export PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT
    else
      cat >&2 <<EOF
SGLang source does not appear patched for ${reason}:
  ${resolved_root}
Required marker set: ${require_mode}
EOF
      return 1
    fi
  else
    if [[ "${require_mode}" = "priority" ]]; then
      PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT=1
      export PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT
    fi
  fi

  PREPARED_SGLANG_ROOT="${resolved_root}"
  export PREPARED_SGLANG_ROOT
  export SGLANG_ROOT="${resolved_root}"
}

precise_print_local_ready_summary() {
  local mode="${1:-transfer}"
  local log_file="${2:-}"
  local root="${PREPARED_SGLANG_ROOT:-$(resolve_precise_sglang_root || true)}"
  local dynamo_root="${SOURCE_DIR:-$(resolve_precise_dynamo_root || true)}"
  local transfer_status="missing"
  local priority_status="n/a"
  local specprefill_status="n/a"

  if [[ -n "${root}" ]] && _precise_sglang_require_markers "${root}" transfer; then
    transfer_status="ok"
  fi

  if [[ "${mode}" = "priority" ]]; then
    if [[ -n "${root}" ]] && _precise_sglang_require_markers "${root}" priority; then
      priority_status="ok"
    elif [[ "${PREPARED_SGLANG_PRIORITY_MARKERS_PRESENT:-1}" = "0" ]]; then
      priority_status="unavailable on pinned/extracted SGLang source"
    else
      priority_status="missing"
    fi
  elif [[ "${mode}" = "specprefill" ]]; then
    if [[ -n "${dynamo_root}" ]] && _precise_dynamo_require_markers "${dynamo_root}" specprefill; then
      specprefill_status="ok"
    else
      specprefill_status="missing"
    fi
  fi

  precise_banner_numbered 2 6 "PRECISE LOCAL READY (the local extracted/patched SGLang source is good)" "${log_file}"
  _precise_sglang_log "Machine profile: ${DYNAMO_MACHINE_PROFILE:-<unset>}" "${log_file}"
  _precise_sglang_log "Frontend image: ${FRONTEND_IMAGE:-<unset>}" "${log_file}"
  _precise_sglang_log "Worker image: ${WORKER_IMAGE:-<unset>}" "${log_file}"
  _precise_sglang_log "Auto-build precise images: ${AUTO_BUILD_PRECISE_IMAGES:-0}" "${log_file}"
  _precise_sglang_log "SGLang root: ${root:-<unresolved>}" "${log_file}"
  _precise_sglang_log "Local transfer markers: ${transfer_status}" "${log_file}"
  if [[ "${mode}" = "priority" ]]; then
    _precise_sglang_log "Local priority markers: ${priority_status}" "${log_file}"
  elif [[ "${mode}" = "specprefill" ]]; then
    _precise_sglang_log "Dynamo root: ${dynamo_root:-<unresolved>}" "${log_file}"
    _precise_sglang_log "Local speculative-prefill markers: ${specprefill_status}" "${log_file}"
  fi
  _precise_sglang_log "Ready to start Dynamo: yes" "${log_file}"
}

precise_print_go_summary() {
  local mode="${1:-transfer}"
  local log_file="${2:-}"
  precise_banner_numbered 6 6 "PRECISE EXPERIMENT GO (smoke test passed and requests are about to start)" "${log_file}"
  _precise_sglang_log "Machine profile: ${DYNAMO_MACHINE_PROFILE:-<unset>}" "${log_file}"
  _precise_sglang_log "Attribution mode: ${mode}" "${log_file}"
  _precise_sglang_log "Smoke test: ok" "${log_file}"
  _precise_sglang_log "Live attribution check: ok" "${log_file}"
  _precise_sglang_log "Requests may now start." "${log_file}"
}
