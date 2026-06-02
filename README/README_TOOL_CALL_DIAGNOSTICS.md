# Tool-Call Diagnostics

Use this before changing AgentBench orchestration. The goal is to prove whether
the current model, Dynamo tool parser, and Deep Agents stack can execute real
tools, not just produce prose that looks like tool calls.

The path under test is:

```text
model -> Dynamo tool parser -> Deep Agents -> tool execution -> model continues
```

## 1. Start Dynamo

Use the same model/parser you plan to benchmark:

```bash
cd ~/kv_cache_offloading

export MODEL_NAME='Qwen/Qwen2.5-Coder-7B-Instruct'
export PYTHONWARNINGS="ignore::DeprecationWarning,ignore::PendingDeprecationWarning"
# Optional, if Hugging Face warns about unauthenticated requests:
# export HF_TOKEN='<your-hugging-face-token>'

./run_dynamo_single_host.sh stop

DYN_TOOL_CALL_PARSER=hermes \
DYNAMO_MODEL_PATH="$MODEL_NAME" \
DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
./run_dynamo_single_host.sh start
```

## 2. Raw Dynamo Tool-Call Probe

This bypasses AgentBench and Deep Agents. It only asks Dynamo for an
OpenAI-style structured tool call.

```bash
cd ~/kv_cache_offloading

python3.11 agentbench/diagnose_dynamo_tool_calls.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME"
```

Success looks like:

```text
tool_calls=1
```

or, in `summary.json`, each case has `tool_call_count > 0`.

If this fails, the problem is before Deep Agents. Investigate model choice,
`DYN_TOOL_CALL_PARSER`, and the raw Dynamo response.

## 3. Deep Agents Multi-Tool Probe

This checks whether Deep Agents receives tool calls, executes them, and feeds
tool results back to the model.

```bash
cd ~/kv_cache_offloading

python3.11 agentbench/diagnose_deepagents_tool_loop.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --case ls-read-execute
```

Success looks like:

```text
tool_calls=2 or more
tool_messages=2 or more
required_tools_observed=True
multi_tool_loop_observed=True
case_success=True
```

Then test a minimal edit/validate loop:

```bash
python3.11 agentbench/diagnose_deepagents_tool_loop.py \
  --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
  --model "$MODEL_NAME" \
  --case edit-validate
```

Success looks like:

```text
required_tools_observed=True
multi_tool_loop_observed=True
result_file_exists=True
edit_validation_observed=True
case_success=True
```

## 4. Output Files

Diagnostics are written under:

```text
experiments/raw/agentbench/diagnostics/
```

Raw Dynamo probe:

```text
dynamo_tool_calls_<timestamp>/
  auto_request.json
  auto_response.json
  required_request.json
  required_response.json
  named_request.json
  named_response.json
  summary.json
```

Deep Agents probe:

```text
deepagents_tool_loop_<timestamp>/
  request.json
  messages.json
  summary.json
  workspace/
```

The most important Deep Agents fields are:

- `ai_tool_call_count`
- `tool_message_count`
- `invalid_tool_call_count`
- `unique_tool_names`
- `required_tools_observed`
- `missing_required_tools`
- `multi_tool_loop_observed`
- `result_file_exists`
- `edit_validation_observed`
- `case_success`

## 5. How To Interpret Results

If raw Dynamo fails:

```text
model/parser is not producing structured tool calls
```

Try a larger model or a different `DYN_TOOL_CALL_PARSER`.

If raw Dynamo passes but Deep Agents fails:

```text
tool calls exist, but the Deep Agents/LangChain path is not executing them
```

Inspect `messages.json` to see whether tool calls are malformed, invalid, or
not being returned to the model.

If both pass:

```text
the model can run a real multi-step tool loop
```

At that point it makes sense to delegate more of the SWE-bench solving loop to
Deep Agents or to add iterative execution steps in the AgentBench harness.

## 6. Model/Parser Matrix

Run the same diagnostics across model/parser combinations:

```bash
for MODEL_NAME in \
  Qwen/Qwen2.5-Coder-7B-Instruct \
  Qwen/Qwen2.5-7B-Instruct
do
  ./run_dynamo_single_host.sh stop

  DYN_TOOL_CALL_PARSER=hermes \
  DYNAMO_MODEL_PATH="$MODEL_NAME" \
  DYNAMO_SERVED_MODEL_NAME="$MODEL_NAME" \
  ./run_dynamo_single_host.sh start

  python3.11 agentbench/diagnose_dynamo_tool_calls.py \
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
    --model "$MODEL_NAME"

  python3.11 agentbench/diagnose_deepagents_tool_loop.py \
    --frontend-url "http://127.0.0.1:${DYNAMO_FRONTEND_PORT:-8000}/v1/chat/completions" \
    --model "$MODEL_NAME" \
    --case ls-read-execute
done
```

Only move to SWE-bench orchestration changes after at least one configuration
passes the Deep Agents multi-tool probe.
