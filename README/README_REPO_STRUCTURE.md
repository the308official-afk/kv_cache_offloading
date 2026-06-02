# Repository Structure

This repository is organized around four active surfaces: runbooks, benchmark
code, runtime instrumentation, and generated experiment artifacts.

## Top-Level Entry Points

- `run_dynamo_single_host.sh`: starts/stops the single-host Dynamo stack.
- `run_dynamo_head.sh`: launches the Dynamo frontend/head services.
- `run_dynamo_worker.sh`: launches the SGLang worker.
- `aws/`: EC2 upload, download, bootstrap, and recovery helpers.

Keep these at the root for now because the runbooks and EC2 workflows call them
directly.

## Documentation

- `README/`: project runbooks, debug notes, roadmap, setup notes, and PDFs.
- `agentbench/README.md`: short pointer into the canonical runbook.
- `runtime_instrumentation/README.md`: instrumentation-specific overview.
- `aws/README.md`: EC2 operations guide.

Use `README/README.md` as the main index.

## Source And Harness Code

- `agentbench/`: custom SWE-bench/DeepAgents harness, prompt construction,
  adapters, sample tasks, and diagnostics.
- `agentbench/deepagents_app/`: local app adapter that talks to Dynamo.
- `upstream/`: cloned or extracted upstream projects used by this repository.
- `upstream/deepagents/`: upstream DeepAgents checkout. Treat as vendored
  upstream code, not primary project code.
- `upstream/dynamo/`: upstream Dynamo checkout used for instrumentation patching
  and image builds.
- `upstream/sglang/`: extracted SGLang source overlay used for transfer logging.
- `runtime_instrumentation/`: source extraction, hot patches, parser scripts,
  and instrumentation overlays.

## Experiments And Generated Outputs

- `experiments/raw/agentbench/results/`: AgentBench run outputs.
- `experiments/scripts/`: runnable experiment scripts and experiment notes.
- `experiments/raw/`: raw profiler captures, logs, transfer JSONL files, and
  first-pass output.
- `experiments/parsed/`: derived CSV/JSON summaries from raw data.
- `experiments/reports/runs/`: curated per-run reports that join AgentBench
  latency/cache metrics, SGLang transfer summaries, run manifests, and outcome
  flags.
- `outputs/`: generated artifacts from local/manual runs.
- `presentations/`: presentation decks and rendered presentation assets.

Generated outputs can be large and noisy. Prefer committing only compact
summaries, scripts, and final reports unless a raw artifact is explicitly needed
for reproducibility.

## Cleanup Rules

- Put new runbooks and notes in `README/`, not the repo root.
- Put EC2 helper scripts in `aws/`.
- Put benchmark harness code in `agentbench/`.
- Put runtime patching/logging tools in `runtime_instrumentation/`.
- Put experiment scripts under `experiments/scripts/`.
- Put raw run products under `experiments/raw/`.
- Put derived summaries under `experiments/parsed/` and final reports under
  `experiments/reports/`.
- Avoid committing `.DS_Store`, temporary Office lock files, and copied raw
  logs unless they are intentionally part of a report.
