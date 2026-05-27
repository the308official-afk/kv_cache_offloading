#!/usr/bin/env python3

"""Select representative top kernels for an Nsight Compute HBM pass."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


DEFAULT_AGENT_PHASES = ("planning", "execution", "patch_generation", "review")
DEFAULT_INFERENCE_PHASES = ("decode", "prefill")
DEFAULT_BUCKETS = ("ffn_mlp", "attention_kv")


def split_csv(value: str | None, default: tuple[str, ...]) -> set[str]:
    if not value:
        return set(default)
    return {item.strip() for item in value.split(",") if item.strip()}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_float(value: str | None) -> float:
    if not value:
        return 0.0
    return float(value)


def regex_token_for_kernel(name: str) -> str:
    token_patterns = [
        r"cutlass_[A-Za-z0-9_]+",
        r"ampere_[A-Za-z0-9_]+",
        r"BatchPrefillWithPagedKVCacheKernel",
        r"PersistentVariableLengthMergeStatesKernel",
        r"FusedAddRMSNormKernel",
        r"RMSNormKernel",
        r"fused_rope_kernel",
        r"create_flashinfer_kv_indices_triton",
        r"gemv2T_kernel_val",
        r"splitKreduce_kernel",
        r"act_and_mul_kernel",
        r"store_kvcache",
    ]
    for pattern in token_patterns:
        match = re.search(pattern, name)
        if match:
            return match.group(0)
    pieces = re.findall(r"[A-Za-z_][A-Za-z0-9_]{8,}", name)
    if pieces:
        return max(pieces, key=len)
    return name[:80]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-agent-phase-kernels", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--top-kernels-per-group", type=int, default=2)
    parser.add_argument("--agent-phases", help="Comma-separated agent phases to include.")
    parser.add_argument("--inference-phases", help="Comma-separated inference phases to include.")
    parser.add_argument("--buckets", help="Comma-separated buckets to include.")
    args = parser.parse_args()

    source = args.top_agent_phase_kernels.resolve()
    if not source.is_file():
        raise SystemExit(f"top agent phase kernels CSV not found: {source}")
    if args.top_kernels_per_group < 1:
        raise SystemExit("--top-kernels-per-group must be >= 1")

    agent_phases = split_csv(args.agent_phases, DEFAULT_AGENT_PHASES)
    inference_phases = split_csv(args.inference_phases, DEFAULT_INFERENCE_PHASES)
    buckets = split_csv(args.buckets, DEFAULT_BUCKETS)

    grouped: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in read_rows(source):
        agent_phase = row.get("agent_phase") or ""
        inference_phase = row.get("inference_phase") or ""
        bucket = row.get("bucket") or ""
        if agent_phase not in agent_phases:
            continue
        if inference_phase not in inference_phases:
            continue
        if bucket not in buckets:
            continue
        key = (agent_phase, inference_phase, bucket)
        grouped.setdefault(key, []).append(row)

    selected: list[dict[str, str]] = []
    seen_names: set[str] = set()
    for key in sorted(grouped):
        rows = sorted(grouped[key], key=lambda row: parse_float(row.get("duration_ms")), reverse=True)
        for row in rows[: args.top_kernels_per_group]:
            kernel_name = row.get("kernel_name") or ""
            regex_token = regex_token_for_kernel(kernel_name)
            next_row = dict(row)
            next_row["regex_token"] = regex_token
            next_row["deduped_kernel"] = "0" if kernel_name in seen_names else "1"
            selected.append(next_row)
            seen_names.add(kernel_name)

    tokens = sorted({row["regex_token"] for row in selected if row.get("regex_token")})
    if not tokens:
        raise SystemExit("No kernels selected. Check phase/bucket filters.")

    # Nsight Compute expects the regex: prefix for regex matching. Keep the
    # expression token-based so it stays shorter than full demangled C++ names.
    kernel_regex = "regex:(?:" + "|".join(re.escape(token) for token in tokens) + ")"

    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    write_rows(out_dir / "selected_top_kernels.csv", selected)
    (out_dir / "selected_kernel_regex.txt").write_text(kernel_regex + "\n", encoding="utf-8")
    (out_dir / "selected_kernel_tokens.txt").write_text("\n".join(tokens) + "\n", encoding="utf-8")

    print(out_dir / "selected_top_kernels.csv")
    print(out_dir / "selected_kernel_regex.txt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
