#!/bin/bash

# Source this file to apply a stable, known-good SGLang source image default
# for extraction/patching. Explicit overrides still win.

: "${SGLANG_PINNED_SOURCE_IMAGE:=lmsysorg/sglang:v0.5.11-cu129-runtime}"
: "${SGLANG_SOURCE_IMAGE:=${SGLANG_PINNED_SOURCE_IMAGE}}"

export SGLANG_PINNED_SOURCE_IMAGE
export SGLANG_SOURCE_IMAGE
