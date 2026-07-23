#!/usr/bin/env bash

# Readable suite config for the sequential agentic-hint wrappers.
# Edit this file when you want one place with clearly separated settings
# for the known-good synthetic and SWE-bench variants of Experiments 9, 11,
# 12, and 13.
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

: "${SUITE_DEFAULT_RUNS:=exp9_synthetic exp9_swebench exp11_synthetic exp11_swebench exp12_synthetic exp12_swebench exp13_synthetic exp13_swebench}"
: "${SUITE_RUNS:=}"
: "${SUITE_EXPERIMENTS:=}"
: "${SUITE_ISOLATION_MODE:=per_case}"
: "${SUITE_DEFAULT_MODE:=sweep}"
: "${SUITE_CONTINUE_ON_ERROR:=0}"
: "${SUITE_INTERACTIVE_BUILD_PROGRESS:=1}"
: "${SUITE_ENSURE_PRECISE_RUNTIME:=auto}"
: "${PRECISE_START_MODE:=clean}"

# Shared logging / proof defaults.
# This config is tuned to match the current GH200 known-good commands.
: "${SGLANG_TRANSFER_LOG:=1}"
: "${SGLANG_TRANSFER_LOG_PROFILE:=full}"

# Shared prompt-isolation defaults
: "${RETENTION_PROMPT_ISOLATION_MODE:=disjoint}"
: "${SPEC_PREFILL_PROMPT_ISOLATION_MODE:=disjoint}"

###############################################################################
# Experiment 9 synthetic: KV retention
###############################################################################

: "${EXP9_SYNTHETIC_MODE:=sweep}"
: "${EXP9_SYNTHETIC_RESET_MODE:=flush}"
: "${EXP9_SYNTHETIC_RETENTION_REQUEST_SOURCE:=synthetic}"
: "${EXP9_SYNTHETIC_RETENTION_ATTRIBUTION_MODE:=precise}"
: "${EXP9_SYNTHETIC_RETENTION_REQUEST_CONTEXT_MODE:=auto}"
: "${EXP9_SYNTHETIC_RETENTION_TOP_LEVEL_PRIORITY_MODE:=disable}"
: "${EXP9_SYNTHETIC_STOP_ON_PROBE_FAILURE:=1}"
: "${EXP9_SYNTHETIC_DISTRACTOR_COUNTS:=100 110 120 130 140 150 160 170 180 190 200}"
: "${EXP9_SYNTHETIC_PROTECTED_INPUT_LEN:=2000}"
: "${EXP9_SYNTHETIC_DISTRACTOR_INPUT_LEN:=2000}"
: "${EXP9_SYNTHETIC_PROTECTED_HINT_PROFILES:=high-priority}"

###############################################################################
# Experiment 9 SWE-bench: KV retention over task prompts
###############################################################################

: "${EXP9_SWEBENCH_MODE:=sweep}"
: "${EXP9_SWEBENCH_RESET_MODE:=flush}"
: "${EXP9_SWEBENCH_RETENTION_REQUEST_SOURCE:=swebench_dataset}"
: "${EXP9_RETENTION_SWEBENCH_DATASET:=ScaleAI/SWE-bench_Pro}"
: "${EXP9_RETENTION_SWEBENCH_SPLIT:=test}"
: "${EXP9_RETENTION_SWEBENCH_INDEX:=0}"
: "${EXP9_SWEBENCH_RETENTION_SWEBENCH_DATASET:=${EXP9_RETENTION_SWEBENCH_DATASET}}"
: "${EXP9_SWEBENCH_RETENTION_SWEBENCH_SPLIT:=${EXP9_RETENTION_SWEBENCH_SPLIT}}"
: "${EXP9_SWEBENCH_RETENTION_SWEBENCH_INDEX:=${EXP9_RETENTION_SWEBENCH_INDEX}}"
: "${EXP9_SWEBENCH_DISTRACTOR_COUNTS:=200 400 730}"
: "${EXP9_SWEBENCH_PROTECTED_HINT_PROFILES:=high-priority}"

###############################################################################
# Experiment 9 trajectory prompts: optional advanced mode
###############################################################################

: "${EXP9_RETENTION_TRAJECTORY_PROMPT_CATALOG:=experiments/reports/latest_swebench_trajectory_prompt_catalog.csv}"
: "${EXP9_RETENTION_TRAJECTORY_PROTECTED_TASK_INDEX:=0}"
: "${EXP9_RETENTION_TRAJECTORY_PROTECTED_INSTANCE_ID:=}"
: "${EXP9_RETENTION_TRAJECTORY_PROTECTED_STAGE:=patch_generation}"
: "${EXP9_RETENTION_TRAJECTORY_STAGES:=planning execution patch_generation review}"
: "${EXP9_RETENTION_TRAJECTORY_PROMPT_PREFIX_MODE:=task_stage}"
: "${EXP9_RETENTION_TRAJECTORY_DISTRACTOR_START_TASK_INDEX:=-1}"
: "${EXP9_RETENTION_TRAJECTORY_ALLOW_DISTRACTOR_REUSE:=0}"
###############################################################################
# Experiment 11 synthetic: Priority scheduling
###############################################################################

: "${EXP11_SYNTHETIC_MODE:=all}"
: "${EXP11_SYNTHETIC_RESET_MODE:=flush}"
: "${EXP11_SYNTHETIC_PRIORITY_REQUEST_SOURCE:=synthetic}"
: "${EXP11_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_AXIS:=PRIORITY_ARRIVAL_GAP_MS}"
: "${EXP11_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_VALUES:=50 100 200 400}"
: "${EXP11_SYNTHETIC_LOW_PRIORITY_COUNT:=8}"
: "${EXP11_SYNTHETIC_HIGH_PRIORITY_COUNT:=4}"
: "${EXP11_SYNTHETIC_PRIORITY_INPUT_LEN:=4000}"
: "${EXP11_SYNTHETIC_PRIORITY_OUTPUT_LEN:=128}"
: "${EXP11_SYNTHETIC_PRIORITY_INTER_REQUEST_GAP_MS:=20}"

###############################################################################
# Experiment 11 SWE-bench: Priority scheduling over task prompts
###############################################################################

: "${EXP11_SWEBENCH_MODE:=all}"
: "${EXP11_SWEBENCH_RESET_MODE:=flush}"
: "${EXP11_SWEBENCH_PRIORITY_REQUEST_SOURCE:=swebench_dataset}"
: "${EXP11_PRIORITY_SWEBENCH_DATASET:=ScaleAI/SWE-bench_Pro}"
: "${EXP11_PRIORITY_SWEBENCH_SPLIT:=test}"
: "${EXP11_PRIORITY_SWEBENCH_START_INDEX:=0}"
: "${EXP11_SWEBENCH_PRIORITY_SWEBENCH_DATASET:=${EXP11_PRIORITY_SWEBENCH_DATASET}}"
: "${EXP11_SWEBENCH_PRIORITY_SWEBENCH_SPLIT:=${EXP11_PRIORITY_SWEBENCH_SPLIT}}"
: "${EXP11_SWEBENCH_PRIORITY_SWEBENCH_START_INDEX:=${EXP11_PRIORITY_SWEBENCH_START_INDEX}}"
: "${EXP11_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_AXIS:=PRIORITY_ARRIVAL_GAP_MS}"
: "${EXP11_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_VALUES:=50 100 200 400}"
: "${EXP11_SWEBENCH_LOW_PRIORITY_COUNT:=8}"
: "${EXP11_SWEBENCH_HIGH_PRIORITY_COUNT:=4}"
: "${EXP11_SWEBENCH_PRIORITY_OUTPUT_LEN:=128}"
: "${EXP11_SWEBENCH_PRIORITY_INTER_REQUEST_GAP_MS:=20}"

###############################################################################
# Experiment 12 synthetic: Speculative prefill
###############################################################################

: "${EXP12_SYNTHETIC_MODE:=all}"
: "${EXP12_SYNTHETIC_RESET_MODE:=flush}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_REQUEST_SOURCE:=synthetic}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_ATTRIBUTION_MODE:=precise}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_REQUEST_CONTEXT_MODE:=auto}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_SWEEP_AXIS:=SPEC_PREFILL_WARMUP_WAIT_MS}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_SWEEP_VALUES:=0 500 1000 2000}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_TURN_A_WORDS:=4000}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_TURN_B_WORDS:=2048}"
: "${EXP12_SYNTHETIC_SPEC_PREFILL_OUTPUT_TOKENS:=128}"

###############################################################################
# Experiment 12 SWE-bench: Speculative prefill over task prompts
###############################################################################

: "${EXP12_SWEBENCH_MODE:=all}"
: "${EXP12_SWEBENCH_RESET_MODE:=restart}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_REQUEST_SOURCE:=swebench_dataset}"
: "${EXP12_SPEC_PREFILL_SWEBENCH_DATASET:=ScaleAI/SWE-bench_Pro}"
: "${EXP12_SPEC_PREFILL_SWEBENCH_SPLIT:=test}"
: "${EXP12_SPEC_PREFILL_TURN_A_INDEX:=0}"
: "${EXP12_SPEC_PREFILL_TURN_B_INDEX:=1}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_SWEBENCH_DATASET:=${EXP12_SPEC_PREFILL_SWEBENCH_DATASET}}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_SWEBENCH_SPLIT:=${EXP12_SPEC_PREFILL_SWEBENCH_SPLIT}}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_TURN_A_INDEX:=${EXP12_SPEC_PREFILL_TURN_A_INDEX}}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_TURN_B_INDEX:=${EXP12_SPEC_PREFILL_TURN_B_INDEX}}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_COMPARISON_MODE:=same_task_isolated}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_SWEEP_AXIS:=SPEC_PREFILL_WARMUP_WAIT_MS}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_SWEEP_VALUES:=0 500 1000 2000}"
: "${EXP12_SWEBENCH_SPEC_PREFILL_OUTPUT_TOKENS:=128}"

###############################################################################
# Experiment 13 synthetic: Latency sensitivity
###############################################################################

: "${EXP13_SYNTHETIC_MODE:=all}"
: "${EXP13_SYNTHETIC_RESET_MODE:=flush}"
: "${EXP13_SYNTHETIC_PRIORITY_REQUEST_SOURCE:=synthetic}"
: "${EXP13_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_AXIS:=PRIORITY_ARRIVAL_GAP_MS}"
: "${EXP13_SYNTHETIC_PRIORITY_SCHEDULING_SWEEP_VALUES:=50 100 200 400}"
: "${EXP13_SYNTHETIC_LOW_PRIORITY_COUNT:=8}"
: "${EXP13_SYNTHETIC_HIGH_PRIORITY_COUNT:=4}"
: "${EXP13_SYNTHETIC_PRIORITY_INPUT_LEN:=4000}"
: "${EXP13_SYNTHETIC_PRIORITY_OUTPUT_LEN:=128}"
: "${EXP13_SYNTHETIC_PRIORITY_INTER_REQUEST_GAP_MS:=20}"

###############################################################################
# Experiment 13 SWE-bench: Latency sensitivity over task prompts
###############################################################################

: "${EXP13_SWEBENCH_MODE:=all}"
: "${EXP13_SWEBENCH_RESET_MODE:=flush}"
: "${EXP13_SWEBENCH_PRIORITY_REQUEST_SOURCE:=swebench_dataset}"
: "${EXP13_SWEBENCH_PRIORITY_SWEBENCH_DATASET:=ScaleAI/SWE-bench_Pro}"
: "${EXP13_SWEBENCH_PRIORITY_SWEBENCH_SPLIT:=test}"
: "${EXP13_SWEBENCH_PRIORITY_SWEBENCH_START_INDEX:=0}"
: "${EXP13_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_AXIS:=PRIORITY_ARRIVAL_GAP_MS}"
: "${EXP13_SWEBENCH_PRIORITY_SCHEDULING_SWEEP_VALUES:=50 100 200 400}"
: "${EXP13_SWEBENCH_LOW_PRIORITY_COUNT:=8}"
: "${EXP13_SWEBENCH_HIGH_PRIORITY_COUNT:=4}"
: "${EXP13_SWEBENCH_PRIORITY_OUTPUT_LEN:=128}"
: "${EXP13_SWEBENCH_PRIORITY_INTER_REQUEST_GAP_MS:=20}"
