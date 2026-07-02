#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_NAME="$(basename "${REPO_ROOT}")"

PEM="/Users/oluwolejaiyeoba/Documents/GitHub/secrets/projectonekeypair.pem"
REMOTE_PROJECT_DIR="/home/ec2-user/${REPO_NAME}"

SERVERS=(
  ""
  "100.26.186.35"
  ""
)
LABELS=("S0" "S1" "S2")

usage() {
  cat <<'EOF'
Usage:
  ./download.sh
    Download AgentBench results, the full experiments/reports tree, and SGLang transfer logs from server 0

  ./download.sh <server-index>
    Download AgentBench results, the full experiments/reports tree, and SGLang transfer logs from the given server

Examples:
  ./download.sh
  ./download.sh 1
EOF
}

REMOTE_RESULTS_DIR="${REMOTE_PROJECT_DIR}/experiments/raw/agentbench/results"
REMOTE_RESULTS_DIR_LEGACY="${REMOTE_PROJECT_DIR}/agentbench/results"
LOCAL_RESULTS_DIR="${REPO_ROOT}/experiments/raw/agentbench/results"
REMOTE_TRANSFER_LOG_DIR="${REMOTE_PROJECT_DIR}/experiments/raw/sglang_transfer_logs"
REMOTE_TRANSFER_REPORT_LEGACY="${REMOTE_PROJECT_DIR}/experiments/sglang_transfer_logs/sglang_transfer_events.jsonl"
LOCAL_TRANSFER_LOG_DIR="${REPO_ROOT}/experiments/raw/sglang_transfer_logs"
REMOTE_RUN_REPORTS_DIR="${REMOTE_PROJECT_DIR}/experiments/reports/runs"
LOCAL_RUN_REPORTS_DIR="${REPO_ROOT}/experiments/reports/runs"
REMOTE_REPORTS_DIR="${REMOTE_PROJECT_DIR}/experiments/reports"
LOCAL_REPORTS_DIR="${REPO_ROOT}/experiments/reports"
REMOTE_PRIORITY_SCHEDULING_REPORTS_DIR="${REMOTE_REPORTS_DIR}/priority_scheduling"
LOCAL_PRIORITY_SCHEDULING_REPORTS_DIR="${LOCAL_REPORTS_DIR}/priority_scheduling"
LOGGING_PROFILE_WALLTIME_REPORT="sglang_logging_profile_walltime.csv"
DESIGN_SPACE_MATRIX_REPORT="design_space_matrix.csv"
DESIGN_SPACE_RETENTION_MATRIX_REPORT="design_space_retention_matrix.csv"
PRIORITY_SCHEDULING_READABLE_REPORT="priority_scheduling_readable.csv"
PRIORITY_SCHEDULING_REQUESTS_REPORT="priority_scheduling_requests.csv"
PRIORITY_SCHEDULING_PROOF_REPORT="priority_scheduling_proof.csv"
PRIORITY_SCHEDULING_SUMMARY_REPORT="priority_scheduling_summary.csv"
PRIORITY_SCHEDULING_SUMMARY_MD_REPORT="priority_scheduling_summary.md"
LATEST_PRIORITY_SCHEDULING_READABLE_REPORT="latest_priority_scheduling_readable.csv"
LATEST_PRIORITY_SCHEDULING_REQUESTS_REPORT="latest_priority_scheduling_requests.csv"
LATEST_PRIORITY_SCHEDULING_PROOF_REPORT="latest_priority_scheduling_proof.csv"
LATEST_PRIORITY_SCHEDULING_SUMMARY_REPORT="latest_priority_scheduling_summary.csv"
LATEST_PRIORITY_SCHEDULING_SUMMARY_MD_REPORT="latest_priority_scheduling_summary.md"
LATEST_PRIORITY_SCHEDULING_RUN_REPORT="latest_priority_scheduling_run.txt"
LATEST_PRIORITY_SCHEDULING_MICROBENCH_MATRIX_REPORT="latest_priority_scheduling_microbenchmark_matrix.csv"
LATEST_PRIORITY_SCHEDULING_MICROBENCH_SUMMARY_REPORT="latest_priority_scheduling_microbenchmark_summary.csv"
LATEST_PRIORITY_SCHEDULING_MICROBENCH_SUMMARY_MD_REPORT="latest_priority_scheduling_microbenchmark_summary.md"
LATEST_PRIORITY_SCHEDULING_MICROBENCH_CONTRACT_REPORT="latest_priority_scheduling_microbenchmark_run_contract.json"
LATEST_SPEC_PREFILL_MICROBENCH_MATRIX_REPORT="latest_speculative_prefill_microbenchmark_matrix.csv"
LATEST_SPEC_PREFILL_MICROBENCH_SUMMARY_REPORT="latest_speculative_prefill_microbenchmark_summary.csv"
LATEST_SPEC_PREFILL_MICROBENCH_SUMMARY_MD_REPORT="latest_speculative_prefill_microbenchmark_summary.md"
LATEST_SPEC_PREFILL_MICROBENCH_CONTRACT_REPORT="latest_speculative_prefill_microbenchmark_run_contract.json"
LATEST_AGENTIC_HINT_SWEEPS_SUITE_SUMMARY_REPORT="latest_agentic_hint_sweeps_suite_summary.md"
LATEST_AGENTIC_HINT_SWEEPS_SUITE_MANIFEST_REPORT="latest_agentic_hint_sweeps_suite_manifest.json"
LATEST_AGENTIC_HINT_SWEEPS_SUITE_DRIVER_LOG="latest_agentic_hint_sweeps_suite_driver.log"
LATEST_RETENTION_PROBE_PROGRESS_REPORT="latest_retention_probe_progress.csv"
LATEST_RETENTION_PROBE_MATRIX_REPORT="latest_retention_probe_matrix.csv"
LATEST_RETENTION_PROBE_REQUESTS_REPORT="latest_retention_probe_requests.csv"
LATEST_RETENTION_PROBE_SUMMARY_REPORT="latest_retention_probe_summary.md"
LATEST_CACHE_CONTROL_RETENTION_THRESHOLD_PROGRESS_REPORT="latest_cache_control_retention_threshold_progress.csv"
LATEST_CACHE_CONTROL_RETENTION_THRESHOLD_MATRIX_REPORT="latest_cache_control_retention_threshold_matrix.csv"
LATEST_CACHE_CONTROL_RETENTION_THRESHOLD_COMPARISON_REPORT="latest_cache_control_retention_threshold_comparison.csv"
LATEST_CACHE_CONTROL_RETENTION_THRESHOLD_SUMMARY_REPORT="latest_cache_control_retention_threshold_summary.md"
LATEST_KV_RETENTION_MICROBENCH_MATRIX_REPORT="latest_kv_retention_microbenchmark_matrix.csv"
LATEST_KV_RETENTION_MICROBENCH_SUMMARY_REPORT="latest_kv_retention_microbenchmark_summary.csv"
LATEST_KV_RETENTION_MICROBENCH_SUMMARY_MD_REPORT="latest_kv_retention_microbenchmark_summary.md"
LATEST_KV_RETENTION_MICROBENCH_CONTRACT_REPORT="latest_kv_retention_microbenchmark_run_contract.json"
RETENTION_THRESHOLD_PROGRESS_REPORT="retention_threshold_sweep_progress.csv"
RETENTION_THRESHOLD_MATRIX_REPORT="retention_threshold_matrix.csv"
RETENTION_THRESHOLD_COMPARISON_REPORT="retention_threshold_comparison.csv"
RETENTION_THRESHOLD_SUMMARY_REPORT="retention_threshold_summary.md"
INDEX="0"

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  INDEX="$1"
fi

if ! [[ "${INDEX}" =~ ^[0-9]+$ ]]; then
  echo "Server index must be numeric: ${INDEX}" >&2
  usage >&2
  exit 1
fi

if (( INDEX < 0 || INDEX >= ${#SERVERS[@]} )); then
  echo "Server index out of range: ${INDEX}" >&2
  echo "Valid indices: 0..$(( ${#SERVERS[@]} - 1 ))" >&2
  exit 1
fi

chmod 400 "$PEM"
mkdir -p "$LOCAL_RESULTS_DIR"
mkdir -p "$LOCAL_TRANSFER_LOG_DIR"
mkdir -p "$LOCAL_RUN_REPORTS_DIR"
mkdir -p "$LOCAL_REPORTS_DIR"
mkdir -p "$LOCAL_PRIORITY_SCHEDULING_REPORTS_DIR"

SSH_OPTS=(
  -i "$PEM"
  -o ControlMaster=auto
  -o ControlPersist=10m
  -o ControlPath=/tmp/kv-cache-offloading-download-%r@%h:%p
  -o StrictHostKeyChecking=accept-new
)
SSH_CMD="ssh ${SSH_OPTS[*]}"

RSYNC_COMMON_OPTS=(
  -az
  --itemize-changes
  --omit-dir-times
  --no-perms
  --no-owner
  --no-group
)

print_local_report_if_present() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    python3 - <<'PY' "${REPO_ROOT}" "${path}"
import os, sys
print("  " + os.path.relpath(sys.argv[2], sys.argv[1]))
PY
  fi
}

ip="${SERVERS[$INDEX]}"
label="${LABELS[$INDEX]}"
remote_host="ec2-user@${ip}"

echo "==== Downloading agentbench results from ${label} (${ip}) ===="
echo "Remote source: ${REMOTE_RESULTS_DIR}/"
echo "Local dest:    ${LOCAL_RESULTS_DIR}/"

if ! ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_RESULTS_DIR}'"; then
  echo "New AgentBench results path not found, checking legacy path..." >&2
  if ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_RESULTS_DIR_LEGACY}'"; then
    REMOTE_RESULTS_DIR="${REMOTE_RESULTS_DIR_LEGACY}"
    echo "Remote source: ${REMOTE_RESULTS_DIR}/"
  else
    echo "Remote results directory does not exist; skipping raw AgentBench results:" >&2
    echo "  ${REMOTE_RESULTS_DIR}" >&2
    echo "  ${REMOTE_RESULTS_DIR_LEGACY}" >&2
    REMOTE_RESULTS_DIR=""
  fi
fi

if [[ -n "${REMOTE_RESULTS_DIR}" ]]; then
  rsync \
    "${RSYNC_COMMON_OPTS[@]}" \
    -e "$SSH_CMD" \
    "${remote_host}:${REMOTE_RESULTS_DIR}/" \
    "${LOCAL_RESULTS_DIR}/"
fi

echo "==== Downloading SGLang transfer reports from ${label} (${ip}) ===="
echo "Remote source: ${REMOTE_TRANSFER_LOG_DIR}/sglang_transfer_events*.jsonl"
echo "Local dest:    ${LOCAL_TRANSFER_LOG_DIR}/"

if ssh "${SSH_OPTS[@]}" "$remote_host" "find '${REMOTE_TRANSFER_LOG_DIR}' -maxdepth 1 -type f -name 'sglang_transfer_events*.jsonl' | grep -q ."; then
  rsync \
    "${RSYNC_COMMON_OPTS[@]}" \
    --include='sglang_transfer_events*.jsonl' \
    --include='latest_sglang_transfer_events.jsonl' \
    --exclude='*' \
    -e "$SSH_CMD" \
    "${remote_host}:${REMOTE_TRANSFER_LOG_DIR}/" \
    "${LOCAL_TRANSFER_LOG_DIR}/"
else
  echo "Timestamped transfer reports not found, checking legacy path..." >&2
  if ssh "${SSH_OPTS[@]}" "$remote_host" "test -f '${REMOTE_TRANSFER_REPORT_LEGACY}'"; then
    echo "Remote source: ${REMOTE_TRANSFER_REPORT_LEGACY}"
    rsync \
      "${RSYNC_COMMON_OPTS[@]}" \
      -e "$SSH_CMD" \
      "${remote_host}:${REMOTE_TRANSFER_REPORT_LEGACY}" \
      "${LOCAL_TRANSFER_LOG_DIR}/"
  else
    echo "Remote SGLang transfer reports do not exist:" >&2
    echo "  ${REMOTE_TRANSFER_LOG_DIR}/sglang_transfer_events*.jsonl" >&2
    echo "  ${REMOTE_TRANSFER_REPORT_LEGACY}" >&2
    exit 1
  fi
fi

echo "==== Downloading full reports tree from ${label} (${ip}) ===="
echo "Remote source: ${REMOTE_REPORTS_DIR}/"
echo "Local dest:    ${LOCAL_REPORTS_DIR}/"

if ssh "${SSH_OPTS[@]}" "$remote_host" "test -d '${REMOTE_REPORTS_DIR}'"; then
  rsync \
    "${RSYNC_COMMON_OPTS[@]}" \
    -e "$SSH_CMD" \
    "${remote_host}:${REMOTE_REPORTS_DIR}/" \
    "${LOCAL_REPORTS_DIR}/"
else
  echo "Remote reports directory not found; skipping full reports sync." >&2
fi

if [[ -x "${REPO_ROOT}/experiments/scripts/agentbench_report/build_run_report.py" ]]; then
  echo "==== Building local latest run report ===="
  if ! python3 "${REPO_ROOT}/experiments/scripts/agentbench_report/build_run_report.py"; then
    echo "Warning: local report builder failed; raw downloads are still present." >&2
  fi
fi

echo "==== Notable local latest reports ===="
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_KV_RETENTION_MICROBENCH_MATRIX_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_KV_RETENTION_MICROBENCH_SUMMARY_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_KV_RETENTION_MICROBENCH_SUMMARY_MD_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_KV_RETENTION_MICROBENCH_CONTRACT_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_PRIORITY_SCHEDULING_MICROBENCH_MATRIX_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_PRIORITY_SCHEDULING_MICROBENCH_SUMMARY_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_PRIORITY_SCHEDULING_MICROBENCH_SUMMARY_MD_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_PRIORITY_SCHEDULING_MICROBENCH_CONTRACT_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_SPEC_PREFILL_MICROBENCH_MATRIX_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_SPEC_PREFILL_MICROBENCH_SUMMARY_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_SPEC_PREFILL_MICROBENCH_SUMMARY_MD_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_SPEC_PREFILL_MICROBENCH_CONTRACT_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_AGENTIC_HINT_SWEEPS_SUITE_SUMMARY_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_AGENTIC_HINT_SWEEPS_SUITE_MANIFEST_REPORT}"
print_local_report_if_present "${LOCAL_REPORTS_DIR}/${LATEST_AGENTIC_HINT_SWEEPS_SUITE_DRIVER_LOG}"

echo "Download complete."
