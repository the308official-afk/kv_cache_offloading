#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

ASSUME_YES=0
DRY_RUN=0

usage() {
  cat <<'EOF'
Usage:
  ./clear_reports.sh [--yes] [--dry-run]

Clears generated experiment outputs:
  - experiments/reports/*
  - experiments/charts/*

This does not clear experiments/raw, experiments/runtime_state, upstream sources,
Docker images, or model caches.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y)
      ASSUME_YES=1
      ;;
    --dry-run)
      DRY_RUN=1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
  shift
done

TARGETS=(
  "experiments/reports"
  "experiments/charts"
)

for target in "${TARGETS[@]}"; do
  mkdir -p "${target}"
  if [[ ! -w "${target}" ]]; then
    echo "Cannot write to ${ROOT_DIR}/${target}" >&2
    exit 1
  fi
done

echo "This will clear generated experiment reports and charts:"
for target in "${TARGETS[@]}"; do
  echo "  ${ROOT_DIR}/${target}"
done
echo
echo "It will not clear experiments/raw, experiments/runtime_state, upstream sources, Docker images, or model caches."

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo
  echo "Dry run. These entries would be deleted:"
  for target in "${TARGETS[@]}"; do
    find "${target}" -mindepth 1 -maxdepth 1 -print
  done
  exit 0
fi

if [[ "${ASSUME_YES}" -ne 1 ]]; then
  echo
  read -r -p "Type DELETE to continue: " CONFIRM
  if [[ "${CONFIRM}" != "DELETE" ]]; then
    echo "Cancelled."
    exit 0
  fi
fi

for target in "${TARGETS[@]}"; do
  find "${target}" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  mkdir -p "${target}"
done

echo
echo "Cleared generated reports and charts."
