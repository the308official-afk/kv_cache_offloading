#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

CONFIRM=0
FORCE_RUNNING=0
INCLUDE_SCREENSHOTS=0

usage() {
  cat <<'EOF'
Usage: experiments/scripts/clean_experiment_data.sh [options]

Clear generated experiment data so the next run starts fresh.

Default mode is a dry run. Pass --yes to actually delete files.

Options:
  --yes                  Delete the listed files/directories.
  --force-running        Allow cleanup while Dynamo containers are running.
  --include-screenshots  Also delete screenshots directly under experiments/.
  -h, --help             Show this help.

Preserved:
  experiments/scripts/
  experiments/README.md
  README/
  agentbench/
  runtime_instrumentation/
  upstream/
  runtime_upstream/
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes)
      CONFIRM=1
      ;;
    --force-running)
      FORCE_RUNNING=1
      ;;
    --include-screenshots)
      INCLUDE_SCREENSHOTS=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

cd "${REPO_ROOT}"

running_dynamo_containers() {
  if ! command -v docker >/dev/null 2>&1; then
    return 0
  fi
  docker ps --format '{{.Names}}' 2>/dev/null | grep -E '^dynamo-' || true
}

if [[ "${FORCE_RUNNING}" != "1" ]]; then
  running="$(running_dynamo_containers)"
  if [[ -n "${running}" ]]; then
    cat >&2 <<EOF
Dynamo containers are running:
${running}

Stop Dynamo first:
  ./run_dynamo_single_host.sh stop

Or rerun this script with --force-running.
EOF
    exit 1
  fi
fi

empty_dirs=(
  "experiments/raw/agentbench/results"
  "experiments/raw/agentbench/diagnostics"
  "experiments/raw/sglang_transfer_logs"
  "experiments/raw/deepagents_swebench_profile"
  "experiments/raw/lpx_decode_split/profiles"
  "experiments/parsed"
  "experiments/reports/runs"
  "experiments/reports/batches"
  "experiments/reports/comparisons"
  "experiments/reports/design_space"
  "experiments/reports/retention_probe"
  "experiments/reports/retention_probe_batches"
  "experiments/reports/deepagents_swebench_profile"
  "experiments/reports/lpx_decode_split"
  "experiments/reports/misc"
)

legacy_empty_dirs=(
  "agentbench/results"
)

top_level_report_patterns=(
  "experiments/reports/all_runs_*"
  "experiments/reports/latest_runs_*"
  "experiments/reports/latest_run_*"
  "experiments/reports/multi_model_batch_overview.csv"
  "experiments/reports/prompt_evolution_*.csv"
  "experiments/reports/sglang_logging_profile_walltime.csv"
  "experiments/reports/design_space_matrix.csv"
  "experiments/reports/design_space_retention_matrix.csv"
)

targets=()

add_dir_contents() {
  local dir="$1"
  [[ -d "${dir}" ]] || return 0
  while IFS= read -r -d '' item; do
    targets+=("${item}")
  done < <(find "${dir}" -mindepth 1 -maxdepth 1 -print0)
}

add_glob_matches() {
  local pattern="$1"
  local match
  shopt -s nullglob
  for match in ${pattern}; do
    targets+=("${match}")
  done
  shopt -u nullglob
}

for dir in "${empty_dirs[@]}" "${legacy_empty_dirs[@]}"; do
  add_dir_contents "${dir}"
done

for pattern in "${top_level_report_patterns[@]}"; do
  add_glob_matches "${pattern}"
done

if [[ "${INCLUDE_SCREENSHOTS}" = "1" ]]; then
  while IFS= read -r -d '' item; do
    targets+=("${item}")
  done < <(find experiments -maxdepth 1 -type f -name 'Screenshot *.png' -print0 2>/dev/null || true)
fi

while IFS= read -r -d '' item; do
  targets+=("${item}")
done < <(find experiments/raw experiments/parsed experiments/reports -name '.DS_Store' -print0 2>/dev/null || true)

deduped_targets=()
for item in "${targets[@]}"; do
  seen=0
  if [[ "${#deduped_targets[@]}" -gt 0 ]]; then
    for existing in "${deduped_targets[@]}"; do
      if [[ "${existing}" = "${item}" ]]; then
        seen=1
        break
      fi
    done
  fi
  if [[ "${seen}" = "0" ]]; then
    deduped_targets+=("${item}")
  fi
done
targets=("${deduped_targets[@]}")

if [[ "${#targets[@]}" -eq 0 ]]; then
  echo "No experiment data found to clean."
  exit 0
fi

echo "Experiment data cleanup targets:"
printf '  %s\n' "${targets[@]}" | sort
echo

if [[ "${CONFIRM}" != "1" ]]; then
  cat <<'EOF'
Dry run only. Nothing was deleted.

To delete these files/directories:
  ./experiments/scripts/clean_experiment_data.sh --yes
EOF
  exit 0
fi

rm -rf -- "${targets[@]}"

for dir in "${empty_dirs[@]}"; do
  mkdir -p "${dir}"
done

echo "Experiment data cleaned."
