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
    "router_pin_status",
    "router_pin_ttls",
    "router_skip_reasons",
    "worker_pin_status",
    "worker_pin_ttls",
    "worker_pin_refreshes",
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
    parser.add_argument("--frontend-log", default="")
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


def extract_first_json_object(payload: str) -> dict | None:
    json_start = payload.find("{")
    if json_start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        parsed, _ = decoder.raw_decode(payload[json_start:])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_cache_pinning_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    events: list[dict] = []
    for raw_line in path.read_text(errors="replace").splitlines():
        marker = "[CACHE_PINNING_JSON]"
        if marker not in raw_line:
            continue
        payload = raw_line.split(marker, 1)[1].strip()
        parsed = extract_first_json_object(payload)
        if not isinstance(parsed, dict):
            continue
        events.append(parsed)
    return events


def summarize_router_pin(frontend_log: Path) -> tuple[str, str, str]:
    events = parse_cache_pinning_events(frontend_log)
    if not frontend_log.exists():
        return "missing", "", ""

    seen = False
    spawned = False
    ttls: set[str] = set()
    skip_reasons: set[str] = set()
    for event in events:
        event_type = str(event.get("event_type", ""))
        ttl = event.get("ttl_seconds", event.get("cache_control_ttl"))
        if ttl not in (None, ""):
            ttls.add(str(ttl))
        if event_type == "router.cache_control_seen":
            seen = True
        elif event_type == "router.pin_state_created":
            seen = True
        elif event_type == "router.pin_prefix_spawned":
            seen = True
            spawned = True
        elif event_type == "router.pin_state_skipped":
            seen = True
            reason = event.get("reason")
            if reason not in (None, ""):
                skip_reasons.add(str(reason))

    if spawned:
        status = "spawned"
    elif seen:
        status = "seen"
    else:
        status = "not_seen"
    return status, "|".join(sorted(ttls)), "|".join(sorted(skip_reasons))


def summarize_worker_pin(worker_log: Path) -> tuple[str, str, str]:
    events = parse_cache_pinning_events(worker_log)
    if not worker_log.exists():
        return "missing", "", ""

    applied = False
    seen = False
    ttls: set[str] = set()
    refreshes = 0
    for event in events:
        event_type = str(event.get("event_type", ""))
        ttl = event.get("ttl_seconds")
        if ttl not in (None, ""):
            ttls.add(str(ttl))
        if event_type == "worker.pin_prefix_applied":
            seen = True
            try:
                applied = applied or int(event.get("nodes_pinned", 0)) > 0
            except Exception:
                pass
        elif event_type in {"worker.pin_refreshed_cache_hit", "worker.pin_refreshed_host_insert"}:
            seen = True
            refreshes += 1

    if applied:
        status = "applied"
    elif seen:
        status = "seen"
    else:
        status = "not_seen"
    return status, "|".join(sorted(ttls)), str(refreshes)


def build_summary(args: argparse.Namespace, requests_rows: list[dict]) -> dict:
    row1 = requests_rows[0] if requests_rows else {}
    row2 = requests_rows[1] if len(requests_rows) > 1 else {}
    turn2_cached = row2.get("cached_tokens", "")
    try:
        cached_positive = int(turn2_cached) > 0
    except Exception:
        cached_positive = False
    router_pin_status, router_pin_ttls, router_skip_reasons = (
        summarize_router_pin(Path(args.frontend_log)) if args.frontend_log else ("missing", "", "")
    )
    worker_pin_status, worker_pin_ttls, worker_pin_refreshes = (
        summarize_worker_pin(Path(args.worker_log)) if args.worker_log else ("missing", "", "")
    )

    verdict = "request_failed"
    if row1.get("http_status", "").startswith("2") and row2.get("http_status", "").startswith("2"):
        if cached_positive and router_pin_status == "spawned" and worker_pin_status == "applied":
            verdict = "pin_path_applied_and_cache_reused"
        elif cached_positive and router_pin_status == "spawned":
            verdict = "router_spawned_pin_and_cache_reused"
        elif cached_positive:
            verdict = "cache_reused"
        else:
            verdict = "no_cached_tokens"

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
        "router_pin_status": router_pin_status,
        "router_pin_ttls": router_pin_ttls,
        "router_skip_reasons": router_skip_reasons,
        "worker_pin_status": worker_pin_status,
        "worker_pin_ttls": worker_pin_ttls,
        "worker_pin_refreshes": worker_pin_refreshes,
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
        f"- router_pin_status: `{summary['router_pin_status']}`",
        f"- router_pin_ttls: `{summary['router_pin_ttls']}`",
        f"- router_skip_reasons: `{summary['router_skip_reasons']}`",
        f"- worker_pin_status: `{summary['worker_pin_status']}`",
        f"- worker_pin_ttls: `{summary['worker_pin_ttls']}`",
        f"- worker_pin_refreshes: `{summary['worker_pin_refreshes']}`",
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
