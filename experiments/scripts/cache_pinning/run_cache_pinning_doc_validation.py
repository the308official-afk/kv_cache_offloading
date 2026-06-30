#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.request
from pathlib import Path


REQUESTS_COLUMNS = [
    "turn",
    "http_status",
    "latency_ms",
    "prompt_tokens",
    "cached_tokens",
    "completion_tokens",
    "response_preview",
    "error",
]

SUMMARY_COLUMNS = [
    "run_id",
    "model",
    "ttl",
    "frontend_flag",
    "turn1_status",
    "turn2_status",
    "turn1_ms",
    "turn2_ms",
    "turn1_cached",
    "turn2_cached",
    "turn2_cache",
    "worker_pin_signal",
    "worker_pin_matches",
    "verdict",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--frontend-url", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--ttl", default="1h")
    parser.add_argument("--turn1-max-tokens", type=int, default=128)
    parser.add_argument("--turn2-max-tokens", type=int, default=128)
    parser.add_argument("--system-prompt", default="You are a helpful assistant.")
    parser.add_argument("--turn1-user", default="Explain how a radix tree works in simple terms.")
    parser.add_argument("--turn2-user", default="Now explain what the leaves store.")
    parser.add_argument("--frontend-flag", default="")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--worker-log", default="")
    parser.add_argument("--postprocess-only", action="store_true")
    return parser.parse_args()


def post_json(url: str, payload: dict) -> tuple[int, dict, str]:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            body = resp.read().decode("utf-8")
            latency_ms = int(round((time.perf_counter() - start) * 1000))
            return resp.status, json.loads(body), str(latency_ms)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        latency_ms = int(round((time.perf_counter() - start) * 1000))
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {"raw_body": body}
        payload["_error"] = body
        return exc.code, payload, str(latency_ms)


def usage_details(resp: dict) -> tuple[str, str, str]:
    usage = resp.get("usage") or {}
    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    prompt_details = usage.get("prompt_tokens_details") or {}
    cached_tokens = prompt_details.get("cached_tokens")
    return (
        "" if prompt_tokens is None else str(prompt_tokens),
        "" if cached_tokens is None else str(cached_tokens),
        "" if completion_tokens is None else str(completion_tokens),
    )


def response_text(resp: dict) -> str:
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception:
        return ""


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def build_worker_pin_signal(worker_log: Path) -> tuple[str, str]:
    if not worker_log.exists():
        return "missing", "0"
    text = worker_log.read_text(errors="replace")
    matches = []
    for needle in (
        "Pinned ",
        "pin_prefix",
        "ttl_seconds",
        "/hicache/pin_prefix",
    ):
        if needle in text:
            matches.append(needle)
    if not matches:
        return "not_seen", "0"
    return "seen", str(len(matches))


def build_summary(args: argparse.Namespace, requests_rows: list[dict]) -> dict:
    row1 = requests_rows[0] if requests_rows else {}
    row2 = requests_rows[1] if len(requests_rows) > 1 else {}
    turn2_cached = row2.get("cached_tokens", "")
    try:
        cached_positive = int(turn2_cached) > 0
    except Exception:
        cached_positive = False
    worker_pin_signal, worker_pin_matches = build_worker_pin_signal(Path(args.worker_log)) if args.worker_log else ("missing", "0")

    verdict = "request_failed"
    if row1.get("http_status", "").startswith("2") and row2.get("http_status", "").startswith("2"):
        verdict = "cache_pinning_worked" if cached_positive else "no_cached_tokens"

    return {
        "run_id": args.run_id,
        "model": args.model,
        "ttl": args.ttl,
        "frontend_flag": args.frontend_flag,
        "turn1_status": row1.get("http_status", ""),
        "turn2_status": row2.get("http_status", ""),
        "turn1_ms": row1.get("latency_ms", ""),
        "turn2_ms": row2.get("latency_ms", ""),
        "turn1_cached": row1.get("cached_tokens", ""),
        "turn2_cached": row2.get("cached_tokens", ""),
        "turn2_cache": "hit" if cached_positive else "miss",
        "worker_pin_signal": worker_pin_signal,
        "worker_pin_matches": worker_pin_matches,
        "verdict": verdict,
    }


def write_summary_md(path: Path, summary: dict) -> None:
    lines = [
        "# Cache-Pinning Doc Validation",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- model: `{summary['model']}`",
        f"- ttl: `{summary['ttl']}`",
        f"- frontend_flag: `{summary['frontend_flag']}`",
        f"- turn1_status: `{summary['turn1_status']}`",
        f"- turn2_status: `{summary['turn2_status']}`",
        f"- turn1_ms: `{summary['turn1_ms']}`",
        f"- turn2_ms: `{summary['turn2_ms']}`",
        f"- turn1_cached: `{summary['turn1_cached']}`",
        f"- turn2_cached: `{summary['turn2_cached']}`",
        f"- turn2_cache: `{summary['turn2_cache']}`",
        f"- worker_pin_signal: `{summary['worker_pin_signal']}`",
        f"- worker_pin_matches: `{summary['worker_pin_matches']}`",
        f"- verdict: `{summary['verdict']}`",
        "",
    ]
    path.write_text("\n".join(lines))


def run_validation(args: argparse.Namespace, out_dir: Path) -> None:
    payload1 = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system_prompt},
            {"role": "user", "content": args.turn1_user},
        ],
        "max_tokens": args.turn1_max_tokens,
        "temperature": 0,
        "stream": False,
        "nvext": {"cache_control": {"type": "ephemeral", "ttl": args.ttl}},
    }

    status1, resp1, latency1 = post_json(args.frontend_url, payload1)
    prompt1, cached1, completion1 = usage_details(resp1)
    assistant_text = response_text(resp1)

    payload2 = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": args.system_prompt},
            {"role": "user", "content": args.turn1_user},
            {"role": "assistant", "content": assistant_text},
            {"role": "user", "content": args.turn2_user},
        ],
        "max_tokens": args.turn2_max_tokens,
        "temperature": 0,
        "stream": False,
        "nvext": {"cache_control": {"type": "ephemeral", "ttl": args.ttl}},
    }

    status2, resp2, latency2 = post_json(args.frontend_url, payload2)
    prompt2, cached2, completion2 = usage_details(resp2)

    rows = [
        {
            "turn": "turn1",
            "http_status": str(status1),
            "latency_ms": latency1,
            "prompt_tokens": prompt1,
            "cached_tokens": cached1,
            "completion_tokens": completion1,
            "response_preview": response_text(resp1)[:200],
            "error": resp1.get("_error", ""),
        },
        {
            "turn": "turn2",
            "http_status": str(status2),
            "latency_ms": latency2,
            "prompt_tokens": prompt2,
            "cached_tokens": cached2,
            "completion_tokens": completion2,
            "response_preview": response_text(resp2)[:200],
            "error": resp2.get("_error", ""),
        },
    ]

    (out_dir / "doc_validation_result.json").write_text(json.dumps({"requests": rows}, indent=2))
    write_csv(out_dir / "doc_validation_requests.csv", rows, REQUESTS_COLUMNS)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.postprocess_only:
        run_validation(args, out_dir)

    result_path = out_dir / "doc_validation_result.json"
    result = json.loads(result_path.read_text())
    requests_rows = result.get("requests", [])
    write_csv(out_dir / "doc_validation_requests.csv", requests_rows, REQUESTS_COLUMNS)

    summary = build_summary(args, requests_rows)
    write_csv(out_dir / "doc_validation_summary.csv", [summary], SUMMARY_COLUMNS)
    write_summary_md(out_dir / "doc_validation_summary.md", summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
