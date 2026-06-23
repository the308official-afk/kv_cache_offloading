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

_precise_sglang_log() {
  local message="$1"
  local log_file="${2:-}"
  if [[ -n "${log_file}" ]]; then
    printf '%s\n' "${message}" | tee -a "${log_file}"
  else
    printf '%s\n' "${message}" >&2
  fi
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
    *)
      echo "Unknown precise SGLang marker mode: ${require_mode}" >&2
      return 2
      ;;
  esac
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
  printf '%s\n' "nvcr.io/nvidia/ai-dynamo/sglang-runtime:1.0.2"
}

prepare_precise_sglang_for_run() {
  local reason="${1:-precise attribution}"
  local log_file="${2:-}"
  local require_mode="${3:-transfer}"
  local py_bin="${PYTHON_BIN:-$(choose_precise_sglang_python)}"
  local resolved_root

  resolved_root="$(resolve_precise_sglang_root || true)"
  if [[ -z "${resolved_root}" ]]; then
    local image
    image="$(resolve_precise_sglang_source_image)"
    _precise_sglang_log "Extracting SGLang source for ${reason}..." "${log_file}"
    _precise_sglang_log "Using pinned/selected SGLang source image: ${image}" "${log_file}"
    _precise_sglang_run "${log_file}" env "SGLANG_IMAGE=${image}" \
      ./runtime_instrumentation/sglang_transfer_logging/extract_sglang_source.sh
    resolved_root="$(resolve_precise_sglang_root || true)"
  else
    _precise_sglang_log "Reusing extracted SGLang source root: ${resolved_root}" "${log_file}"
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
