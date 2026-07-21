#!/usr/bin/env bash

# Machine-readable latency-sensitivity microbenchmark contract.
#
# This experiment intentionally reuses the priority-scheduling burst harness,
# but sends nvext.agent_hints.latency_sensitivity instead of nvext.agent_hints.priority.

CONTRACT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${ROOT_DIR:-$(cd "${CONTRACT_DIR}/.." && pwd)}"

: "${LATENCY_SENSITIVITY_MODE:=all}"
: "${LATENCY_SENSITIVITY_ID:=latency_sensitivity_microbenchmark_$(date +%Y%m%d_%H%M%S)}"
: "${LATENCY_SENSITIVITY_LOW_VALUE:=0.2}"
: "${LATENCY_SENSITIVITY_HIGH_VALUE:=1.0}"

: "${PRIORITY_SCHEDULING_MODE:=${LATENCY_SENSITIVITY_MODE}}"
: "${PRIORITY_SCHEDULING_ID:=${LATENCY_SENSITIVITY_ID}}"
: "${PRIORITY_HINT_KIND:=latency_sensitivity}"
: "${LOW_LATENCY_SENSITIVITY_VALUE:=${LATENCY_SENSITIVITY_LOW_VALUE}}"
: "${HIGH_LATENCY_SENSITIVITY_VALUE:=${LATENCY_SENSITIVITY_HIGH_VALUE}}"
: "${PRIORITY_TOP_LEVEL_PRIORITY_MODE:=disable}"
: "${PRIORITY_SCHEDULING_MICROBENCH_DISPLAY_NAME:=LATENCY SENSITIVITY}"
: "${PRIORITY_SCHEDULING_MICROBENCH_REPORT_TITLE:=Latency Sensitivity Microbenchmark}"
: "${PRIORITY_SCHEDULING_LATEST_PREFIX_REL:=experiments/reports/latest_latency_sensitivity_microbenchmark}"
: "${PRIORITY_SCHEDULING_OUT_ROOT_REL:=experiments/reports/latency_sensitivity_microbenchmark}"
: "${PRIORITY_SCHEDULING_SHARED_MATRIX_NAME:=exp13_latencysens_matrix.csv}"
: "${PRIORITY_SCHEDULING_SHARED_JUMP_AHEAD_NAME:=exp13_latencysens_jump_ahead_vs_arrival_gap.svg}"
: "${PRIORITY_SCHEDULING_PUBLIC_WRAPPER:=${ROOT_DIR}/agentbench/run_latency_sensitivity_microbenchmark_single_host.sh}"
: "${PRIORITY_SCHEDULING_DECISION_PROOF_HELPER:=experiments/scripts/priority_scheduling/build_latency_sensitivity_decision_proof.py}"
: "${PRIORITY_SCHEDULING_DECISION_PROOF_REPORTS_CSV:=experiments/reports/latest_exp13_decision_proof.csv}"
: "${PRIORITY_SCHEDULING_DECISION_PROOF_REPORTS_MD:=experiments/reports/latest_exp13_decision_proof.md}"
: "${PRIORITY_SCHEDULING_DECISION_PROOF_CHARTS_CSV:=experiments/charts/exp13_decision_proof.csv}"
: "${PRIORITY_SCHEDULING_DECISION_PROOF_CHARTS_MD:=experiments/charts/exp13_decision_proof.md}"

# shellcheck disable=SC1091
source "${CONTRACT_DIR}/priority_scheduling_microbenchmark.contract.sh"

export LATENCY_SENSITIVITY_MODE
export LATENCY_SENSITIVITY_ID
export LATENCY_SENSITIVITY_LOW_VALUE
export LATENCY_SENSITIVITY_HIGH_VALUE
export PRIORITY_HINT_KIND
export LOW_LATENCY_SENSITIVITY_VALUE
export HIGH_LATENCY_SENSITIVITY_VALUE
export PRIORITY_TOP_LEVEL_PRIORITY_MODE
export PRIORITY_SCHEDULING_MICROBENCH_DISPLAY_NAME
export PRIORITY_SCHEDULING_MICROBENCH_REPORT_TITLE
export PRIORITY_SCHEDULING_LATEST_PREFIX_REL
export PRIORITY_SCHEDULING_OUT_ROOT_REL
export PRIORITY_SCHEDULING_SHARED_MATRIX_NAME
export PRIORITY_SCHEDULING_SHARED_JUMP_AHEAD_NAME
export PRIORITY_SCHEDULING_PUBLIC_WRAPPER
export PRIORITY_SCHEDULING_DECISION_PROOF_HELPER
export PRIORITY_SCHEDULING_DECISION_PROOF_REPORTS_CSV
export PRIORITY_SCHEDULING_DECISION_PROOF_REPORTS_MD
export PRIORITY_SCHEDULING_DECISION_PROOF_CHARTS_CSV
export PRIORITY_SCHEDULING_DECISION_PROOF_CHARTS_MD
