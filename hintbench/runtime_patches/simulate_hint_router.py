#!/usr/bin/env python3

"""Offline simulator for the first hint-aware routing policy.

Given a workload file or a prior run directory, simulate which worker the
policy would choose for each request using simple cache/load state.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hintbench.runtime_patches.hint_router_policy import (  # noqa: E402
    WorkerSnapshot,
    choose_worker,
)


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def simulate(workload_rows: list[dict], worker_ids: list[str]) -> list[dict]:
    cache_tokens = {worker_id: 0 for worker_id in worker_ids}
    queue_depth = {worker_id: 0.0 for worker_id in worker_ids}
    kv_hit_rate = {worker_id: 0.0 for worker_id in worker_ids}
    decisions: list[dict] = []

    for row in workload_rows:
        workers = [
            WorkerSnapshot(
                worker_id=worker_id,
                queue_depth=queue_depth[worker_id],
                cached_prefix_tokens=cache_tokens[worker_id],
                recent_kv_hit_rate=kv_hit_rate[worker_id],
            )
            for worker_id in worker_ids
        ]
        decision = choose_worker(workers, row.get("hint_payload"))

        chosen = decision.worker_id
        cached_now = cache_tokens[chosen]
        new_tokens = len(row.get("messages", [])) * 32

        cache_tokens[chosen] = min(512, max(cached_now, new_tokens))
        kv_hit_rate[chosen] = 1.0 if cached_now > 0 else 0.0
        queue_depth[chosen] = max(queue_depth[chosen] + 1.0, 1.0)
        for worker_id in worker_ids:
            if worker_id != chosen:
                queue_depth[worker_id] = max(queue_depth[worker_id] - 0.5, 0.0)

        decisions.append(
            {
                "request_id": row.get("request_id"),
                "prompt_id": row.get("prompt_id"),
                "shared_prefix_group": row.get("shared_prefix_group"),
                "hint_payload": row.get("hint_payload"),
                "chosen_worker_id": chosen,
                "score": round(decision.score, 4),
                "cache_score": round(decision.cache_score, 4),
                "load_score": round(decision.load_score, 4),
                "priority_score": round(decision.priority_score, 4),
                "explanation": decision.explanation,
            }
        )

    return decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload-file", help="Path to a workload.jsonl file.")
    parser.add_argument(
        "--run-dir",
        help="Optional HintBench run directory. If set, workload.jsonl will be loaded from there.",
    )
    parser.add_argument(
        "--worker-ids",
        nargs="+",
        default=["worker-a", "worker-b"],
        help="Worker ids to simulate.",
    )
    parser.add_argument("--output-file", help="Optional JSONL output path for decisions.")
    args = parser.parse_args()

    if not args.workload_file and not args.run_dir:
        raise SystemExit("Provide either --workload-file or --run-dir.")

    if args.run_dir:
        workload_path = Path(args.run_dir) / "workload.jsonl"
    else:
        workload_path = Path(args.workload_file)

    rows = load_jsonl(workload_path)
    decisions = simulate(rows, args.worker_ids)

    if args.output_file:
        out = Path(args.output_file)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            "\n".join(json.dumps(row, ensure_ascii=True) for row in decisions) + "\n",
            encoding="utf-8",
        )
    else:
        for row in decisions:
            print(json.dumps(row, ensure_ascii=True))


if __name__ == "__main__":
    main()
