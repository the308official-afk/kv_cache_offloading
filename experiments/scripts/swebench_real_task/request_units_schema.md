# SWE-bench Real Request Units Schema

This directory defines the shared real-task request layer for SWE-bench Pro.

The goal is simple:

- keep the existing runtime and experiment wrappers stable
- postprocess finished Experiment 6 runs
- normalize each real phase request into one reusable request unit

## Main Output

Primary CSV:

- `request_units.csv`

Latest top-level copy:

- `experiments/reports/latest_swebench_real_request_units.csv`

## One Row Means

One row is one real SWE-bench request phase from one finished Experiment 6 run.

Examples:

- planning request
- execution request
- patch_generation request
- review request

## Core Columns

- `request_unit_id`
  - stable row id for downstream reuse
- `task_index`
  - batch index used in the Experiment 6 run
- `run_id`
  - Experiment 6 run id
- `repo`
  - SWE-bench repo
- `instance_id`
  - SWE-bench instance id
- `model`
  - model used for the run
- `phase`
  - planning / execution / patch_generation / review
- `phase_group`
  - compact phase label for grouping
- `phase_attempt`
  - retry-style attempt id when available
- `sequence_index`
  - order within the run
- `step_index`
  - request step index from request_context
- `step_title`
  - human-readable step title
- `request_id`
  - request-level runtime id
- `parent_run_id`
  - parent task run id
- `request_family`
  - shared family id for the whole real task
- `request_kind`
  - compact request type label
- `prompt_hash`
  - hash of the exact prompt text
- `prompt_chars`
  - prompt size in characters
- `prompt_tokens`
  - prompt tokens from measurement data
- `cached_prompt_tokens`
  - cached prompt tokens from measurement data
- `completion_tokens`
  - completion tokens from measurement data
- `latency_ms`
  - request latency from measurement data
- `finish_reason`
  - finish reason from measurement data
- `tool_call_count`
  - number of observed tool calls
- `observed_tool_names`
  - compact pipe-separated list of tool names
- `workspace_patch_nonempty`
  - whether the run produced a non-empty patch
- `prompt_text_path`
  - exact prompt text file for this request unit
- `request_unit_json`
  - structured JSON payload with prompt, context, hints, measurement, and tool-call details

## Screening Columns

- `suitable_for_exp9`
- `suitable_for_exp11`
- `suitable_for_exp12`

These are only first-pass screening flags. They are not final experiment
eligibility proofs.

## Companion Output

Task-level summary:

- `experiments/reports/latest_swebench_real_task_selection.csv`
- `experiments/reports/latest_swebench_real_task_selection.md`

That file groups request units back into whole SWE-bench tasks and shows which
tasks look most promising for Experiments 9, 11, and 12.
