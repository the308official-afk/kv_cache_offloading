#!/bin/bash

# Source this file to use the isolated cache-pinning validation stack.
# This intentionally does not change the default pinned stack used by the
# other experiments.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MACHINE_PROFILE="${DYNAMO_MACHINE_PROFILE:-default}"

: "${CACHE_PINNING_DYNAMO_SOURCE_REPO:=https://github.com/ai-dynamo/dynamo.git}"
: "${CACHE_PINNING_DYNAMO_SOURCE_REF:=7d3d4ec8e4ae865af2f903b21b4afabca28e1940}"
: "${CACHE_PINNING_DYNAMO_PULL_REF:=6213}"
: "${CACHE_PINNING_DYNAMO_SOURCE_DIR:=${ROOT_DIR}/upstream/dynamo_cache_pinning}"

: "${CACHE_PINNING_SGLANG_SOURCE_REPO:=https://github.com/sgl-project/sglang.git}"
: "${CACHE_PINNING_SGLANG_SOURCE_REF:=ff2f70b0fcb6b3ea130c46927ed98edf69d5c17c}"
: "${CACHE_PINNING_SGLANG_PULL_REF:=18941}"
: "${CACHE_PINNING_SGLANG_SOURCE_DIR:=${ROOT_DIR}/upstream/sglang_cache_pinning}"
: "${CACHE_PINNING_SGLANG_ROOT:=${CACHE_PINNING_SGLANG_SOURCE_DIR}/python/sglang}"

: "${CACHE_PINNING_FRONTEND_IMAGE:=local/dynamo-frontend:cache-pinning-${MACHINE_PROFILE}}"
: "${CACHE_PINNING_WORKER_IMAGE:=local/dynamo-sglang:cache-pinning-${MACHINE_PROFILE}}"
: "${CACHE_PINNING_EPP_IMAGE:=registry.k8s.io/gateway-api-inference-extension/epp:v0.5.1}"

export CACHE_PINNING_DYNAMO_SOURCE_REPO
export CACHE_PINNING_DYNAMO_SOURCE_REF
export CACHE_PINNING_DYNAMO_PULL_REF
export CACHE_PINNING_DYNAMO_SOURCE_DIR
export CACHE_PINNING_SGLANG_SOURCE_REPO
export CACHE_PINNING_SGLANG_SOURCE_REF
export CACHE_PINNING_SGLANG_PULL_REF
export CACHE_PINNING_SGLANG_SOURCE_DIR
export CACHE_PINNING_SGLANG_ROOT
export CACHE_PINNING_FRONTEND_IMAGE
export CACHE_PINNING_WORKER_IMAGE
export CACHE_PINNING_EPP_IMAGE
