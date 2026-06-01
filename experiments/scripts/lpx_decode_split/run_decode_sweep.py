#!/usr/bin/env python3

"""Run prompt/output sweeps through Dynamo for decode-split research."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RESULTS_ROOT = REPO_ROOT / "experiments" / "reports" / "lpx_decode_split" / "results"
DEFAULT_FRONTEND_URL = "http://127.0.0.1:8000/v1/chat/completions"
DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def parse_int_list(raw: str) -> list[int]:
    values: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        value = int(part)
        if value <= 0:
            raise argparse.ArgumentTypeError(f"values must be positive: {raw}")
        values.append(value)
    if not values:
        raise argparse.ArgumentTypeError("at least one value is required")
    return values


def make_run_dir(results_root: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = results_root / f"decode-sweep_{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def make_prompt(target_tokens: int, max_tokens: int) -> str:
    # Roughly 4 chars/token is good enough for sweep shape. The response usage
    # tells us the tokenizer's actual prompt token count after the request.
    target_chars = max(256, target_tokens * 4)
    header = (
        "You are participating in a hardware-aware LLM serving experiment.\n"
        "The goal is to stress the decode path with a controlled synthetic "
        "agentic context. Read the context, then answer with a concise numbered "
        f"list of exactly {min(8, max(1, max_tokens // 16))} observations.\n\n"
        "Synthetic agent workspace context:\n"
    )
    chunk = (
        "The agent is inspecting a repository, preserving request hints, "
        "tracking KV-cache reuse, comparing attention pressure with FFN compute, "
        "and deciding whether decode-heavy phases deserve specialized hardware. "
    )
    body_parts = []
    current = len(header)
    while current < target_chars:
        body_parts.append(chunk)
        current += len(chunk)
    return header + "".join(body_parts)


def build_payload(
    *,
    model: str,
    prompt: str,
    max_tokens: int,
    probe_id: str,
    prompt_token_target: int,
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "nvext": {
            "agent_hints": {
                "hint_probe_id": probe_id,
                "program_id": "experiments.lpx_decode_split.decode_sweep",
                "agent_phase": "decode_sweep",
                "expected_output_tokens": max_tokens,
                "prefill_weight": prompt_token_target,
                "decode_weight": max_tokens,
                "reuse_likelihood": 0.2,
                "priority": 3,
            },
            "request_context": {
                "experiment": "lpx_decode_split",
                "prompt_token_target": prompt_token_target,
                "max_tokens": max_tokens,
            },
        },
    }


def post_json(url: str, payload: dict[str, Any], timeout: float) -> tuple[dict[str, Any], float]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return json.loads(raw.decode("utf-8")), elapsed_ms


def flatten_measurement(record: dict[str, Any]) -> dict[str, Any]:
    usage = record.get("usage") or {}
    return {
        "run_id": record["run_id"],
        "timestamp": record["timestamp"],
        "probe_id": record["probe_id"],
        "model": record["model"],
        "prompt_token_target": record["prompt_token_target"],
        "max_tokens": record["max_tokens"],
        "repeat_index": record["repeat_index"],
        "latency_ms": round(record["latency_ms"], 3) if record.get("latency_ms") is not None else None,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cached_tokens": record.get("cached_tokens"),
        "completion_tokens_per_second": record.get("completion_tokens_per_second"),
        "response_id": record.get("response_id"),
        "finish_reason": record.get("finish_reason"),
        "error": record.get("error"),
    }


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def make_summary(rows: list[dict[str, Any]], run_dir: Path) -> str:
    successful = [row for row in rows if not row.get("error")]
    lines = [
        "# Decode Sweep Summary",
        "",
        f"Run directory: `{run_dir}`",
        "",
        f"Total requests: {len(rows)}",
        f"Successful requests: {len(successful)}",
        "",
        "## Group Averages",
        "",
        "| prompt target | max tokens | n | avg latency ms | avg completion tok/s | avg prompt tokens | avg completion tokens |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    groups: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for row in successful:
        key = (int(row["prompt_token_target"]), int(row["max_tokens"]))
        groups.setdefault(key, []).append(row)
    for (prompt_target, max_tokens), group in sorted(groups.items()):
        latencies = [float(row["latency_ms"]) for row in group if row.get("latency_ms") is not None]
        tok_s = [
            float(row["completion_tokens_per_second"])
            for row in group
            if row.get("completion_tokens_per_second") is not None
        ]
        prompt_tokens = [float(row["prompt_tokens"]) for row in group if row.get("prompt_tokens") is not None]
        completion_tokens = [
            float(row["completion_tokens"]) for row in group if row.get("completion_tokens") is not None
        ]
        avg_latency = f"{statistics.mean(latencies):.1f}" if latencies else "n/a"
        avg_tok_s = f"{statistics.mean(tok_s):.2f}" if tok_s else "n/a"
        avg_prompt = f"{statistics.mean(prompt_tokens):.1f}" if prompt_tokens else "n/a"
        avg_completion = f"{statistics.mean(completion_tokens):.1f}" if completion_tokens else "n/a"
        lines.append(
            f"| {prompt_target} | {max_tokens} | {len(group)} | "
            f"{avg_latency} | {avg_tok_s} | {avg_prompt} | {avg_completion} |"
        )
    lines.extend(
        [
            "",
            "## Hardware Interpretation",
            "",
            "- Latency growth with prompt target suggests attention/KV pressure.",
            "- Latency growth with output tokens suggests decode-loop pressure.",
            "- Pair this run with `nsys`/`ncu` to split kernel time into attention/KV versus FFN/GEMM buckets.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend-url", default=DEFAULT_FRONTEND_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--prompt-token-targets", type=parse_int_list, default=parse_int_list("1024,4096,8192"))
    parser.add_argument("--max-tokens-list", type=parse_int_list, default=parse_int_list("64,256"))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=600.0)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--fail-on-error", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.repeats <= 0:
        raise SystemExit("--repeats must be positive")

    run_dir = make_run_dir(args.results_root)
    jsonl_path = run_dir / "measurements.jsonl"
    csv_path = run_dir / "measurements.csv"
    summary_path = run_dir / "summary.md"
    config_path = run_dir / "config.json"
    run_id = run_dir.name

    config = {
        "run_id": run_id,
        "frontend_url": args.frontend_url,
        "model": args.model,
        "prompt_token_targets": args.prompt_token_targets,
        "max_tokens_list": args.max_tokens_list,
        "repeats": args.repeats,
        "timeout": args.timeout,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

    flat_rows: list[dict[str, Any]] = []
    error_count = 0
    with jsonl_path.open("w", encoding="utf-8") as jsonl:
        for prompt_target in args.prompt_token_targets:
            for max_tokens in args.max_tokens_list:
                for repeat in range(args.repeats):
                    probe_id = f"{run_id}::ctx{prompt_target}::out{max_tokens}::r{repeat}"
                    prompt = make_prompt(prompt_target, max_tokens)
                    payload = build_payload(
                        model=args.model,
                        prompt=prompt,
                        max_tokens=max_tokens,
                        probe_id=probe_id,
                        prompt_token_target=prompt_target,
                    )
                    record: dict[str, Any] = {
                        "run_id": run_id,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "probe_id": probe_id,
                        "model": args.model,
                        "frontend_url": args.frontend_url,
                        "prompt_token_target": prompt_target,
                        "prompt_chars": len(prompt),
                        "max_tokens": max_tokens,
                        "repeat_index": repeat,
                    }
                    print(f"Running {probe_id}", flush=True)
                    try:
                        response, latency_ms = post_json(args.frontend_url, payload, args.timeout)
                        usage = response.get("usage") or {}
                        choices = response.get("choices") or []
                        choice = choices[0] if choices else {}
                        finish_reason = choice.get("finish_reason")
                        completion_tokens = usage.get("completion_tokens")
                        tok_s = None
                        if completion_tokens is not None and latency_ms > 0:
                            tok_s = round(float(completion_tokens) / (latency_ms / 1000.0), 4)
                        prompt_details = usage.get("prompt_tokens_details") or {}
                        record.update(
                            {
                                "latency_ms": latency_ms,
                                "usage": usage,
                                "cached_tokens": prompt_details.get("cached_tokens"),
                                "completion_tokens_per_second": tok_s,
                                "response_id": response.get("id"),
                                "finish_reason": finish_reason,
                                "response_preview": json.dumps(response)[:1000],
                            }
                        )
                    except Exception as exc:  # noqa: BLE001 - experiment should keep going.
                        record["error"] = str(exc)
                        error_count += 1
                        print(f"ERROR {probe_id}: {exc}", file=sys.stderr, flush=True)
                    jsonl.write(json.dumps(record, sort_keys=True) + "\n")
                    jsonl.flush()
                    flat_rows.append(flatten_measurement(record))

    write_csv(csv_path, flat_rows)
    summary_path.write_text(make_summary(flat_rows, run_dir), encoding="utf-8")
    print(f"Wrote {run_dir}")
    if args.fail_on_error and error_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
