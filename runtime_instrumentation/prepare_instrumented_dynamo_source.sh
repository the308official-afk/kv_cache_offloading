#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}/upstream/dynamo}"

echo "Preparing instrumented Dynamo source at: ${SOURCE_DIR}"

if [[ ! -d "${SOURCE_DIR}/.git" ]]; then
  echo "Dynamo source repo not found. Fetching upstream source..."
  "${SCRIPT_DIR}/fetch_dynamo_source.sh"
fi

echo "Applying runtime JSON logging patch if needed..."
if "${SCRIPT_DIR}/apply_runtime_json_logging_patch.sh"; then
  :
else
  echo "Runtime JSON logging patch did not apply cleanly."
  echo "Continuing with repair steps; they make partially patched source usable."
fi

echo "Applying agent-hint preservation patch if needed..."
"${SCRIPT_DIR}/apply_dynamo_hint_preservation_patch.sh"

echo "Repairing hint-aware worker logging fields..."
python3 "${SCRIPT_DIR}/repair_dynamo_hint_logging_source.py"

echo "Repairing known Dynamo router field rename mismatch..."
python3 "${SCRIPT_DIR}/repair_dynamo_router_field_rename.py"

echo "Repairing known Dynamo stream choice stop_reason mismatch..."
python3 "${SCRIPT_DIR}/repair_dynamo_stream_choice_stop_reason.py"

echo "Verifying required instrumentation markers..."

required_markers=(
  "components/src/dynamo/common/runtime_logging.py:agent_hint_log_fields"
  "components/src/dynamo/common/runtime_logging.py:_maybe_register_transfer_runtime_event"
  "components/src/dynamo/sglang/request_handlers/llm/decode_handler.py:agent_hint_log_fields"
  "components/src/dynamo/sglang/request_handlers/llm/prefill_handler.py:agent_hint_log_fields"
  "lib/llm/src/preprocessor.rs:runtime_observability_extra_args_from_nvext"
  "lib/llm/src/protocols/openai/nvext.rs:expected_output_tokens"
)

for marker in "${required_markers[@]}"; do
  file="${marker%%:*}"
  pattern="${marker#*:}"
  if ! grep -q "${pattern}" "${SOURCE_DIR}/${file}"; then
    echo "Missing required marker '${pattern}' in ${SOURCE_DIR}/${file}" >&2
    exit 1
  fi
done

if grep -R "overlap_score_credit" -n "${SOURCE_DIR}/lib" >/dev/null 2>&1; then
  echo "Stale overlap_score_credit references remain:" >&2
  grep -R "overlap_score_credit" -n "${SOURCE_DIR}/lib" >&2
  exit 1
fi

if grep -R "choice.stop_reason = None" -n "${SOURCE_DIR}/lib/llm/src/preprocessor.rs" >/dev/null 2>&1; then
  echo "Stale choice.stop_reason assignment remains in preprocessor.rs" >&2
  grep -R "choice.stop_reason = None" -n "${SOURCE_DIR}/lib/llm/src/preprocessor.rs" >&2
  exit 1
fi

cat <<EOF

Instrumented Dynamo source is ready.

Next:
  cd ${ROOT_DIR}
  DYN_RUNTIME_JSON_LOGS=1 ./runtime_instrumentation/build_instrumented_dynamo_images.sh

EOF
