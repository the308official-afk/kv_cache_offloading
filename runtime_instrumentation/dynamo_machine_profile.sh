#!/bin/bash

# Source this file to apply machine-specific defaults for Dynamo image tags and
# build platform. Explicitly provided environment variables still win.

_dynamo_apply_machine_profile() {
  local profile="${DYNAMO_MACHINE_PROFILE:-}"

  case "${profile}" in
    ""|default|none)
      return 0
      ;;
    ec2)
      : "${FRONTEND_IMAGE_TAG:=local/dynamo-frontend:runtime-json-logs-ec2}"
      : "${WORKER_IMAGE_TAG:=local/dynamo-sglang:runtime-json-logs-ec2}"
      : "${FRONTEND_IMAGE:=${FRONTEND_IMAGE_TAG}}"
      : "${WORKER_IMAGE:=${WORKER_IMAGE_TAG}}"
      # Leave platform unset on EC2/x86 so docker uses the native host default.
      : "${DOCKER_BUILD_PLATFORM:=}"
      ;;
    gh200)
      : "${FRONTEND_IMAGE_TAG:=local/dynamo-frontend:runtime-json-logs-gh200}"
      : "${WORKER_IMAGE_TAG:=local/dynamo-sglang:runtime-json-logs-gh200}"
      : "${FRONTEND_IMAGE:=${FRONTEND_IMAGE_TAG}}"
      : "${WORKER_IMAGE:=${WORKER_IMAGE_TAG}}"
      : "${DOCKER_BUILD_PLATFORM:=linux/arm64}"
      ;;
    *)
      echo "Unknown DYNAMO_MACHINE_PROFILE: ${profile}" >&2
      echo "Valid values: ec2 gh200" >&2
      return 1
      ;;
  esac

  if [[ -n "${DOCKER_BUILD_PLATFORM:-}" ]]; then
    : "${TARGET_PLATFORM:=${DOCKER_BUILD_PLATFORM}}"
  fi

  export DYNAMO_MACHINE_PROFILE
  export FRONTEND_IMAGE_TAG
  export WORKER_IMAGE_TAG
  export FRONTEND_IMAGE
  export WORKER_IMAGE
  export DOCKER_BUILD_PLATFORM
  export TARGET_PLATFORM
}

_dynamo_apply_machine_profile

