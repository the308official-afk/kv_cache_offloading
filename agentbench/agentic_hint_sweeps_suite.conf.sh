#!/usr/bin/env bash

# Readable suite config for the sequential agentic-hint wrappers.
# Edit this file when you want one place with clearly separated settings
# for Experiments 9, 11, and 12.
#
# Run with:
#   ./agentbench/run_agentic_hint_sweeps_suite_single_host.sh <model>
# or:
#   ./agentbench/run_agentic_hint_sweeps_suite_nohup.sh <model>
#
# You can also point the suite at an alternate file:
#   SUITE_CONFIG_PATH=path/to/another_suite.conf.sh ./agentbench/run_agentic_hint_sweeps_suite_single_host.sh <model>

###############################################################################
# Shared suite settings
###############################################################################

: "${SUITE_EXPERIMENTS:=9 11 12}"
: "${SUITE_ISOLATION_MODE:=flush}"
: "${SUITE_DEFAULT_MODE:=sweep}"
: "${SUITE_CONTINUE_ON_ERROR:=0}"
: "${SUITE_INTERACTIVE_BUILD_PROGRESS:=1}"
: "${SUITE_ENSURE_PRECISE_RUNTIME:=auto}"
: "${PRECISE_START_MODE:=clean}"

# Shared logging / proof defaults.
# This config is tuned to match the current GH200 trio for Experiments 9, 11,
# and 12.
: "${SGLANG_TRANSFER_LOG:=1}"
: "${SGLANG_TRANSFER_LOG_PROFILE:=full}"

# Shared prompt-isolation defaults
: "${RETENTION_PROMPT_ISOLATION_MODE:=disjoint}"
: "${SPEC_PREFILL_PROMPT_ISOLATION_MODE:=disjoint}"

###############################################################################
# Experiment 9: KV retention
###############################################################################

: "${EXP9_MODE:=sweep}"
: "${EXP9_RETENTION_REQUEST_SOURCE:=synthetic}"
: "${EXP9_RETENTION_SWEBENCH_DATASET:=ScaleAI/SWE-bench_Pro}"
: "${EXP9_RETENTION_SWEBENCH_SPLIT:=test}"
: "${EXP9_RETENTION_SWEBENCH_INDEX:=0}"
: "${EXP9_RETENTION_SWEBENCH_INSTANCE_ID:=}"
: "${EXP9_RETENTION_SWEBENCH_DISTRACTOR_START_INDEX:=-1}"
: "${EXP9_RETENTION_SWEBENCH_ALLOW_DISTRACTOR_REUSE:=0}"
: "${EXP9_RETENTION_TRAJECTORY_PROMPT_CATALOG:=experiments/reports/latest_swebench_trajectory_prompt_catalog.csv}"
: "${EXP9_RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX:=0}"
: "${EXP9_RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID:=}"
: "${EXP9_RETENTION_TRAJECTORY_PROTECTED_STAGE:=patch_generation}"
: "${EXP9_RETENTION_TRAJECTORY_STAGES:=planning execution patch_generation review}"
: "${EXP9_RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX:=-1}"
: "${EXP9_RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE:=0}"
: "${EXP9_RETENTION_ATTRIBUTION_MODE:=precise}"
: "${EXP9_RETENTION_REQUEST_CONTEXT_MODE:=auto}"
: "${EXP9_RETENTION_TOP_LEVEL_PRIORITY_MODE:=disable}"
: "${EXP9_STOP_ON_PROBE_FAILURE:=1}"
: "${EXP9_DISTRACTOR_COUNTS:=100 110 120 130 140 150 160 170 180 190 200}"
: "${EXP9_PROTECTED_INPUT_LEN:=2000}"
: "${EXP9_DISTRACTOR_INPUT_LEN:=2000}"
: "${EXP9_PROTECTED_HINT_PROFILES:=high-priority}"

###############################################################################
# Experiment 11: Priority scheduling
###############################################################################

: "${EXP11_MODE:=all}"
: "${EXP11_PRIORITY_SCHEDULING_SWEEP_AXIS:=PRIORITY_ARRIVAL_GAP_MS}"
: "${EXP11_PRIORITY_SCHEDULING_SWEEP_VALUES:=50 100 200 400}"
: "${EXP11_LOW_PRIORITY_COUNT:=8}"
: "${EXP11_HIGH_PRIORITY_COUNT:=4}"
: "${EXP11_PRIORITY_INPUT_LEN:=4000}"
: "${EXP11_PRIORITY_OUTPUT_LEN:=128}"
: "${EXP11_PRIORITY_INTER_REQUEST_GAP_MS:=20}"

###############################################################################
# Experiment 12: Speculative prefill
###############################################################################

: "${EXP12_MODE:=all}"
: "${EXP12_SPEC_PREFILL_ATTRIBUTION_MODE:=precise}"
: "${EXP12_SPEC_PREFILL_REQUEST_CONTEXT_MODE:=auto}"
: "${EXP12_SPEC_PREFILL_SWEEP_AXIS:=SPEC_PREFILL_WARMUP_WAIT_MS}"
: "${EXP12_SPEC_PREFILL_SWEEP_VALUES:=0 500 1000 2000}"
: "${EXP12_SPEC_PREFILL_TURN_A_WORDS:=4000}"
: "${EXP12_SPEC_PREFILL_TURN_B_WORDS:=2048}"
: "${EXP12_SPEC_PREFILL_OUTPUT_TOKENS:=128}"
