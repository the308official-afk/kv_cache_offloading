#!/usr/bin/env bash

# Shared AgentBench runtime defaults.
# Update AGENTBENCH_MODEL here when you want future runs to use a different model.

# AGENTBENCH_MODEL="${AGENTBENCH_MODEL:-Qwen/Qwen2.5-0.5B}"
AGENTBENCH_MODEL="${AGENTBENCH_MODEL:-Qwen/Qwen2.5-7B-Instruct}"
AGENTBENCH_FRONTEND_URL="${AGENTBENCH_FRONTEND_URL:-http://127.0.0.1:8000/v1/chat/completions}"
