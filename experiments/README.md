# Experiments

Experiment assets are split by role:

- `scripts/`: runnable experiment scripts and experiment-specific notes.
- `raw/`: raw logs, profiler captures, transfer event JSONL files, and other
  large first-pass outputs.
- `parsed/`: parser outputs such as CSV summaries derived from raw logs.
- `reports/`: curated run summaries and final report-like outputs.

Current experiment families:

- `scripts/lpx_decode_split/`
- `scripts/deepagents_swebench_profile/`
- `scripts/agentbench_report/`
- `raw/agentbench/results/`
- `raw/sglang_transfer_logs/`
- `reports/runs/`

Prefer adding new experiment code under `scripts/<experiment_name>/` and writing
new generated outputs under `raw/`, `parsed/`, or `reports/`.
