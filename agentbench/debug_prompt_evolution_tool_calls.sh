#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

MODEL_NAME="${1:-${TOOL_DEBUG_MODEL:-${MODEL_NAME:-Qwen/Qwen3-Coder-30B-A3B-Instruct-FP8}}}"
FRONTEND_URL="${TOOL_DEBUG_FRONTEND_URL:-http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions}"
if [[ -z "${PYTHON_BIN:-}" ]]; then
  if command -v python3.11 >/dev/null 2>&1; then
    PYTHON_BIN="python3.11"
  else
    PYTHON_BIN="python3"
  fi
fi
RUN_ID="${TOOL_DEBUG_RUN_ID:-tool_call_debug_$(date +%Y%m%d_%H%M%S)}"
OUT_DIR="experiments/reports/tool_call_debug/${RUN_ID}"
RECENT_ROWS="${TOOL_DEBUG_RECENT_ROWS:-20}"
DEEPAGENTS_CASE="${TOOL_DEBUG_DEEPAGENTS_CASE:-edit-validate}"
AGENTBENCH_TOOL_LOOP_RECURSION_LIMIT="${AGENTBENCH_TOOL_LOOP_RECURSION_LIMIT:-12}"
AGENTBENCH_TOOL_LOOP_TIMEOUT_SECONDS="${AGENTBENCH_TOOL_LOOP_TIMEOUT_SECONDS:-180}"
AGENTBENCH_DIAGNOSTIC_SHELL_TIMEOUT_SECONDS="${AGENTBENCH_DIAGNOSTIC_SHELL_TIMEOUT_SECONDS:-$((AGENTBENCH_TOOL_LOOP_TIMEOUT_SECONDS + 60))}"
AGENTBENCH_DEEPAGENTS_SOURCE="${AGENTBENCH_DEEPAGENTS_SOURCE:-upstream}"
AGENTBENCH_FORCE_TOOL_CHOICE="${AGENTBENCH_FORCE_TOOL_CHOICE:-auto}"
AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT="${AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT:-1}"
AGENTBENCH_REQUIRE_GENERAL_PURPOSE_SUBAGENT_DISABLE="${AGENTBENCH_REQUIRE_GENERAL_PURPOSE_SUBAGENT_DISABLE:-1}"
DEEPAGENTS_READY_HELPER="${DEEPAGENTS_READY_HELPER:-./agentbench/ensure_deepagents_ready.sh}"
export AGENTBENCH_DEEPAGENTS_SOURCE
export AGENTBENCH_FORCE_TOOL_CHOICE
export AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT
export AGENTBENCH_REQUIRE_GENERAL_PURPOSE_SUBAGENT_DISABLE
export AGENTBENCH_TOOL_LOOP_RECURSION_LIMIT
export AGENTBENCH_TOOL_LOOP_TIMEOUT_SECONDS

mkdir -p "${OUT_DIR}"

section() {
  echo
  echo "========================================"
  echo "$1"
  echo "========================================"
}

run_with_log() {
  local log_file="$1"
  shift
  if [[ "${AGENTBENCH_DIAGNOSTIC_SHELL_TIMEOUT_SECONDS}" != "0" ]] && command -v timeout >/dev/null 2>&1; then
    timeout "${AGENTBENCH_DIAGNOSTIC_SHELL_TIMEOUT_SECONDS}s" "$@" 2>&1 | tee "${log_file}"
  else
    "$@" 2>&1 | tee "${log_file}"
  fi
  return "${PIPESTATUS[0]}"
}

section "PROMPT EVOLUTION TOOL-CALL DEBUG"
echo "Model: ${MODEL_NAME}"
echo "Frontend URL: ${FRONTEND_URL}"
echo "Python: ${PYTHON_BIN}"
echo "Deep Agents source: ${AGENTBENCH_DEEPAGENTS_SOURCE}"
echo "Deep Agents forced tool choice: ${AGENTBENCH_FORCE_TOOL_CHOICE}"
echo "Disable Deep Agents general-purpose subagent: ${AGENTBENCH_DISABLE_GENERAL_PURPOSE_SUBAGENT}"
echo "Deep Agents diagnostic recursion limit: ${AGENTBENCH_TOOL_LOOP_RECURSION_LIMIT}"
echo "Deep Agents diagnostic timeout seconds: ${AGENTBENCH_TOOL_LOOP_TIMEOUT_SECONDS}"
echo "Outer shell timeout seconds: ${AGENTBENCH_DIAGNOSTIC_SHELL_TIMEOUT_SECONDS}"
echo "Output dir: ${OUT_DIR}"
echo
echo "This script does not start Dynamo."
echo "Run it while the same Dynamo runtime from Experiment 6 is still up."

section "STEP -1: ENSURE DEEP AGENTS IS READY"
"${DEEPAGENTS_READY_HELPER}"

section "STEP 0: LOCAL FILE CHECK"
missing=0
for path in \
  "agentbench/diagnose_dynamo_tool_calls.py" \
  "agentbench/diagnose_deepagents_tool_loop.py" \
  "upstream/deepagents/libs/deepagents/pyproject.toml"
do
  if [[ -f "${path}" ]]; then
    echo "ok: ${path}"
  else
    echo "missing: ${path}"
    missing=1
  fi
done
if [[ "${missing}" == "1" ]]; then
  echo "Required diagnostic script is missing; stopping."
  exit 1
fi

section "STEP 1: CHECK WHETHER EXPERIMENT 6 STARTED DYNAMO WITH TOOL PARSER"
latest_batch_dir="$(ls -td experiments/reports/batches/prompt_evolution_batch_* 2>/dev/null | head -1 || true)"
if [[ -n "${latest_batch_dir}" && -f "${latest_batch_dir}/prompt_evolution_batch_driver.log" ]]; then
  echo "Latest batch dir: ${latest_batch_dir}"
  grep -n "Tool-call parser" "${latest_batch_dir}/prompt_evolution_batch_driver.log" \
    | tee "${OUT_DIR}/latest_batch_tool_parser.txt" || true
  grep -n "Reasoning parser" "${latest_batch_dir}/prompt_evolution_batch_driver.log" \
    | tee "${OUT_DIR}/latest_batch_reasoning_parser.txt" || true
else
  echo "No prompt evolution batch driver log found yet."
fi

section "STEP 2: CHECK RECENT PROMPT-EVOLUTION TOOL COUNTS"
"${PYTHON_BIN}" - <<'PY' "${RECENT_ROWS}" "${OUT_DIR}"
from __future__ import annotations

import csv
import sys
from pathlib import Path

recent_rows = int(sys.argv[1])
out_dir = Path(sys.argv[2])

def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def as_int(value: str | None) -> int:
    try:
        return int(value or "0")
    except ValueError:
        return 0

execution_path = Path("experiments/reports/all_runs_execution_prompts.csv")
overview_path = Path("experiments/reports/all_runs_overview.csv")

execution_rows = read_rows(execution_path)
overview_rows = read_rows(overview_path)
latest_execution = execution_rows[-recent_rows:]
latest_overview = overview_rows[-recent_rows:]

summary_path = out_dir / "recent_prompt_evolution_rows.tsv"
with summary_path.open("w", encoding="utf-8") as f:
    f.write("kind\trun_id\tphase\ttool_call_count\ttools_called\tpatch_bytes\n")
    for row in latest_execution:
        f.write(
            "execution\t"
            f"{row.get('run_id', '')}\t"
            f"{row.get('phase', '')}\t"
            f"{row.get('tool_call_count', '')}\t"
            f"{row.get('tools_called', '')}\t"
            f"{row.get('patch_bytes', '')}\n"
        )
    for row in latest_overview:
        f.write(
            "overview\t"
            f"{row.get('run_id', '')}\t"
            f"{row.get('phase', '')}\t"
            f"{row.get('total_tool_calls', '')}\t"
            f"{row.get('tools_called', row.get('unique_tools', ''))}\t"
            f"{row.get('patch_bytes', '')}\n"
        )

recent_execution_tools = sum(as_int(row.get("tool_call_count")) for row in latest_execution)
recent_overview_tools = sum(as_int(row.get("total_tool_calls")) for row in latest_overview)

print(f"execution_prompts_csv: {execution_path if execution_path.exists() else 'missing'}")
print(f"overview_csv: {overview_path if overview_path.exists() else 'missing'}")
print(f"recent_execution_rows: {len(latest_execution)}")
print(f"recent_execution_tool_calls: {recent_execution_tools}")
print(f"recent_overview_rows: {len(latest_overview)}")
print(f"recent_overview_tool_calls: {recent_overview_tools}")
print(f"saved_recent_rows: {summary_path}")
if latest_execution:
    print()
    print("Latest execution rows:")
    print("run_id\tphase\ttool_call_count\ttools_called\tpatch_bytes")
    for row in latest_execution[-10:]:
        print(
            f"{row.get('run_id', '')}\t"
            f"{row.get('phase', '')}\t"
            f"{row.get('tool_call_count', '')}\t"
            f"{row.get('tools_called', '')}\t"
            f"{row.get('patch_bytes', '')}"
        )
PY

section "STEP 3: DIRECT DYNAMO TOOL-CALL TEST"
echo "Goal: any case should show tool_calls=1."
run_with_log "${OUT_DIR}/dynamo_tool_calls.log" \
  "${PYTHON_BIN}" agentbench/diagnose_dynamo_tool_calls.py \
    --frontend-url "${FRONTEND_URL}" \
    --model "${MODEL_NAME}" \
    --cases auto,required,named \
    --max-tokens 256 \
    --output-dir "${OUT_DIR}/dynamo_tool_calls"
echo "Direct Dynamo diagnostic exit status: 0"

"${PYTHON_BIN}" - <<'PY' "${OUT_DIR}"
from __future__ import annotations

import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
summary_path = out_dir / "dynamo_tool_calls" / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
cases = summary.get("cases") if isinstance(summary.get("cases"), list) else []
counts = [
    int(case.get("tool_call_count") or 0)
    for case in cases
    if isinstance(case, dict)
]
print(f"Direct Dynamo tool-call counts: {counts}")
if not any(count > 0 for count in counts):
    raise SystemExit(
        "CRITICAL FAIL: direct Dynamo produced zero structured tool calls in every case."
    )
PY

section "STEP 4: DEEP AGENTS TOOL LOOP TEST"
echo "Goal: tool_calls > 0, multi_tool_loop_observed=True, case_success=True."
run_with_log "${OUT_DIR}/deepagents_tool_loop.log" \
  "${PYTHON_BIN}" agentbench/diagnose_deepagents_tool_loop.py \
    --frontend-url "${FRONTEND_URL}" \
    --model "${MODEL_NAME}" \
    --case "${DEEPAGENTS_CASE}" \
    --output-dir "${OUT_DIR}/deepagents_tool_loop"
echo "Deep Agents diagnostic exit status: 0"

"${PYTHON_BIN}" - <<'PY' "${OUT_DIR}"
from __future__ import annotations

import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
summary_path = out_dir / "deepagents_tool_loop" / "summary.json"
summary = json.loads(summary_path.read_text(encoding="utf-8"))
tool_calls = int(summary.get("ai_tool_call_count") or 0)
tool_messages = int(summary.get("tool_message_count") or 0)
multi_tool_loop = bool(summary.get("multi_tool_loop_observed"))
case_success = bool(summary.get("case_success"))
print(f"Deep Agents tool calls: {tool_calls}")
print(f"Deep Agents tool messages: {tool_messages}")
print(f"Deep Agents multi-tool loop observed: {multi_tool_loop}")
print(f"Deep Agents case success: {case_success}")
if not case_success:
    raise SystemExit(
        "CRITICAL FAIL: Deep Agents did not complete the required multi-tool loop."
    )
PY

section "STEP 5: SIMPLE INTERPRETATION"
"${PYTHON_BIN}" - <<'PY' "${OUT_DIR}" "0" "0"
from __future__ import annotations

import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
dynamo_status = int(sys.argv[2])
deepagents_status = int(sys.argv[3])

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

dynamo = load_json(out_dir / "dynamo_tool_calls" / "summary.json")
deep = load_json(out_dir / "deepagents_tool_loop" / "summary.json")

dynamo_cases = dynamo.get("cases") if isinstance(dynamo.get("cases"), list) else []
dynamo_counts = [
    int(case.get("tool_call_count") or 0)
    for case in dynamo_cases
    if isinstance(case, dict)
]
dynamo_pass = any(count > 0 for count in dynamo_counts)

deep_tool_calls = int(deep.get("ai_tool_call_count") or 0)
deep_tool_messages = int(deep.get("tool_message_count") or 0)
deep_loop = bool(deep.get("multi_tool_loop_observed"))
deep_success = bool(deep.get("case_success"))

lines = []
lines.append("# Prompt Evolution Tool-Call Debug Summary")
lines.append("")
lines.append(f"- direct_dynamo_exit_status: `{dynamo_status}`")
lines.append(f"- direct_dynamo_tool_call_counts: `{dynamo_counts}`")
lines.append(f"- direct_dynamo_pass: `{dynamo_pass}`")
lines.append(f"- deepagents_exit_status: `{deepagents_status}`")
lines.append(f"- deepagents_tool_calls: `{deep_tool_calls}`")
lines.append(f"- deepagents_tool_messages: `{deep_tool_messages}`")
lines.append(f"- deepagents_multi_tool_loop_observed: `{deep_loop}`")
lines.append(f"- deepagents_case_success: `{deep_success}`")
lines.append("")
lines.append("## Meaning")

if not dynamo_pass:
    verdict = "direct_dynamo_tool_calls_missing"
    lines.append("Dynamo/SGLang/model did not return OpenAI-style tool calls.")
    lines.append("This is below Deep Agents, so Experiment 6 cannot produce real tool traces yet.")
elif not deep_success:
    verdict = "deepagents_tool_loop_missing"
    lines.append("Dynamo can produce tool calls, but Deep Agents did not complete the tool loop.")
    lines.append("The likely issue is Deep Agents/LangChain tool binding or tool-result handling.")
else:
    verdict = "tool_calls_work"
    lines.append("Direct Dynamo and Deep Agents tool calls both worked.")
    lines.append("If Experiment 6 still shows zeros, debug the SWE-bench prompt/evolution loop.")

lines.append("")
lines.append(f"- verdict: `{verdict}`")

summary_path = out_dir / "tool_call_debug_summary.md"
summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

print("\n".join(lines))
print()
print(f"Summary file: {summary_path}")
PY

section "DONE"
echo "Full debug output: ${OUT_DIR}"
