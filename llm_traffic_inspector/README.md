# Local LLM Traffic Inspector

This is a local reverse proxy for inspecting requests from AI coding-agent harnesses.

It lets you route traffic like this:

```text
Codex or Claude Code -> local proxy -> real LLM provider
```

The goal is to answer:

```text
What headers and JSON fields does the agent harness send to the model server?
```

It is designed for traffic you deliberately route through localhost. It does not intercept browser traffic, bypass TLS, steal credentials, or modify your Codex or Claude Code config.

## What It Can See

It can inspect:

- request headers
- request JSON body structure
- provider-specific fields
- streaming SSE events
- response status and safe response headers
- usage fields when providers return them
- cached-token fields when providers return them
- candidate hint fields such as `service_tier`, `cache_control`, `reasoning`, and `nvext`

It cannot see:

- provider internal scheduler decisions
- encrypted traffic that was not explicitly sent to this proxy
- ChatGPT.com or Claude.ai browser traffic
- local shell commands executed by an agent

## Install

Use Python 3.11 or newer.

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector

python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If `python3.11` is not installed, install Python 3.11+ first. Do not use the system Python 3.9 on macOS for this app.

## Safe Mode

Safe mode is the default:

```bash
LLM_PROXY_CAPTURE_MODE=safe
```

Safe mode does not store prompt text, source code, tool arguments, or tool results. It stores field names, counts, sizes, and hashes.

## Full Local Research Mode

Full mode stores the redacted JSON request body locally:

```bash
LLM_PROXY_CAPTURE_MODE=full
```

Use it only for local research. It may capture private source code, prompts, tool outputs, file contents, environment details, and accidental secrets. Authentication headers and obvious secret fields are still redacted in logs.

Captured logs are ignored by git.

## Start A Mock Upstream

Start this first so you can test without making any paid API call:

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
source .venv/bin/activate

LLM_PROXY_MOCK_PORT=8799 \
python -m llm_traffic_inspector.run_mock_upstream
```

Leave it running.

## Start The Proxy Against The Mock

Open a second terminal:

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
source .venv/bin/activate

LLM_PROXY_PROVIDER=custom \
LLM_PROXY_UPSTREAM_BASE_URL=http://127.0.0.1:8799 \
LLM_PROXY_UPSTREAM_AUTH_MODE=none \
LLM_PROXY_CAPTURE_MODE=safe \
LLM_PROXY_LOG_DIRECTORY=./logs/mock \
LLM_PROXY_PORT=8787 \
python -m llm_traffic_inspector.run_proxy
```

The proxy binds only to:

```text
127.0.0.1
```

## Test With Curl

Open a third terminal:

```bash
curl -N http://127.0.0.1:8787/v1/chat/completions \
  -H 'Authorization: Bearer local-placeholder-only' \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "mock-model",
    "stream": true,
    "service_tier": "priority",
    "nvext": {
      "agent_hints": {
        "priority": 10,
        "latency_sensitivity": "high",
        "osl": 128
      }
    },
    "messages": [
      {"role": "system", "content": "You are a test assistant."},
      {"role": "user", "content": "Say hello."}
    ]
  }'
```

You should see streamed `data:` events. The proxy terminal should print one readable request summary.

## Inspect Logs

Logs are JSONL files:

```bash
ls -lah ./logs/mock
tail -n 1 ./logs/mock/traffic_*.jsonl
```

In safe mode, prompt text is not stored.

## Generate A Hint Report

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
source .venv/bin/activate

python -m llm_traffic_inspector.report \
  --log-dir ./logs/mock \
  --output-csv ./logs/mock/hint_report.csv \
  --overview-csv ./logs/mock/traffic_overview.csv
```

The report shows:

- header names observed
- JSON field paths observed
- candidate hint fields
- hint category
- safe example value
- percentage of requests containing each field

## OpenAI Proxy

Start the proxy in one terminal:

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
source .venv/bin/activate

export LLM_PROXY_PROVIDER=openai
export LLM_PROXY_UPSTREAM_BASE_URL=https://api.openai.com
export LLM_PROXY_OPENAI_API_KEY="actual-openai-key"
export LLM_PROXY_CAPTURE_MODE=safe
export LLM_PROXY_LOG_DIRECTORY=./logs/openai
export LLM_PROXY_PORT=8787

python -m llm_traffic_inspector.run_proxy
```

In the separate terminal where you run Codex, use only a harmless placeholder:

```bash
export LOCAL_LLM_PROXY_TOKEN="local-placeholder-only"
```

Then temporarily add a provider like this to your Codex config:

```toml
model_provider = "traffic_inspector"

[model_providers.traffic_inspector]
name = "Local Traffic Inspector"
base_url = "http://127.0.0.1:8787/v1"
env_key = "LOCAL_LLM_PROXY_TOKEN"
wire_api = "responses"
supports_websockets = false
```

Select a model available to your OpenAI API account. Do not permanently overwrite your normal Codex provider.

This proxy replaces:

```text
Authorization: Bearer local-placeholder-only
```

with:

```text
Authorization: Bearer <LLM_PROXY_OPENAI_API_KEY>
```

## Claude Code Proxy

Start the proxy in one terminal:

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
source .venv/bin/activate

export LLM_PROXY_PROVIDER=anthropic
export LLM_PROXY_UPSTREAM_BASE_URL=https://api.anthropic.com
export LLM_PROXY_ANTHROPIC_API_KEY="actual-anthropic-key"
export LLM_PROXY_CAPTURE_MODE=safe
export LLM_PROXY_LOG_DIRECTORY=./logs/anthropic
export LLM_PROXY_PORT=8788

python -m llm_traffic_inspector.run_proxy
```

In a separate terminal for Claude Code:

```bash
export ANTHROPIC_BASE_URL="http://127.0.0.1:8788"
export ANTHROPIC_API_KEY="local-placeholder-only"
claude
```

Keep the actual Anthropic key only in the proxy terminal. Keep the placeholder only in the Claude Code terminal.

To verify Claude Code is using the local gateway, watch the proxy terminal for request summaries and check:

```bash
ls -lah ~/kv_cache_offloading/llm_traffic_inspector/logs/anthropic
```

## Dynamo Or Custom Server Proxy

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
source .venv/bin/activate

LLM_PROXY_PROVIDER=custom \
LLM_PROXY_UPSTREAM_BASE_URL=http://my-dynamo-server:8000 \
LLM_PROXY_UPSTREAM_AUTH_MODE=none \
LLM_PROXY_CAPTURE_MODE=safe \
LLM_PROXY_LOG_DIRECTORY=./logs/dynamo \
LLM_PROXY_PORT=8789 \
python -m llm_traffic_inspector.run_proxy
```

For a custom server that needs pass-through auth:

```bash
LLM_PROXY_UPSTREAM_AUTH_MODE=pass_through
```

For an OpenAI-compatible provider that needs bearer auth:

```bash
LLM_PROXY_PROVIDER=openai_compatible
LLM_PROXY_UPSTREAM_AUTH_MODE=bearer
LLM_PROXY_UPSTREAM_API_KEY="actual-provider-key"
```

## Candidate Hint Categories

The analyzer classifies candidate fields as:

- infrastructure scheduling hint
- cache-control hint
- routing or affinity hint
- workload-shape hint
- model-compute hint
- service-class hint
- agent/workflow context
- observability-only metadata
- standard generation parameter
- authentication or protocol metadata
- unknown candidate field

Examples:

```text
nvext.agent_hints.priority        -> infrastructure scheduling hint
cache_control                     -> cache-control hint
service_tier                      -> service-class hint
reasoning_effort                  -> model-compute hint
max_tokens                        -> standard generation parameter
anthropic-beta header             -> protocol metadata
traceparent                       -> observability metadata
```

## Stop The Proxy

In the proxy terminal:

```bash
Ctrl-C
```

## Return To Normal Codex Or Claude Code

For Codex:

- remove or stop selecting the temporary `traffic_inspector` provider
- return to your usual provider/model settings

For Claude Code:

```bash
unset ANTHROPIC_BASE_URL
unset ANTHROPIC_API_KEY
```

Then start `claude` normally.

## Delete Captured Logs

```bash
cd ~/kv_cache_offloading/llm_traffic_inspector
rm -rf ./logs
```

Only do this after saving any reports you still need.

## Troubleshooting

If the proxy refuses to start:

- check `LLM_PROXY_UPSTREAM_BASE_URL`
- check the port is free
- check you are using Python 3.11+
- check the bind host is exactly `127.0.0.1`

If OpenAI or Anthropic returns authentication errors:

- make sure the real key is set in the proxy terminal
- make sure the harness terminal only uses the placeholder
- do not use OAuth or subscription tokens with this proxy

If streaming does not appear:

- make sure the client request contains `"stream": true`
- use `curl -N`
- check the proxy terminal for request summaries

If no hints are detected:

- inspect `traffic_overview.csv` for all JSON field paths
- remember that not every provider exposes scheduling/cache hints
- headers alone may not contain hint fields

## Paid Provider Calls

Do not make paid provider calls until you have first tested the mock upstream.

Before a real OpenAI, Anthropic, DeepSeek, Kimi, Qwen, or custom paid request, review the exact command and API key environment variables.

