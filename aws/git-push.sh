#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  ./git-push.sh "commit message"
  ./git-push.sh                 # uses an automatic timestamped message

What it does:
  1. changes into the repo root
  2. shows git status
  3. stages all changes
  4. creates a commit (if there are changes)
  5. pushes the current branch to origin
EOF
}

if [[ "${1:-}" = "-h" || "${1:-}" = "--help" ]]; then
  usage
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is not installed or not on PATH" >&2
  exit 1
fi

cd "${REPO_ROOT}"

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Not inside a git repository: ${REPO_ROOT}" >&2
  exit 1
fi

BRANCH="$(git branch --show-current)"
if [[ -z "${BRANCH}" ]]; then
  echo "Could not determine current branch (detached HEAD?)" >&2
  exit 1
fi

COMMIT_MESSAGE="${1:-auto: update $(date +%Y-%m-%d_%H-%M-%S)}"

echo "Repo root: ${REPO_ROOT}"
echo "Branch:    ${BRANCH}"
echo
git status --short
echo

git add -A

if git diff --cached --quiet; then
  echo "No staged changes to commit."
else
  git commit -m "${COMMIT_MESSAGE}"
fi

if git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >/dev/null 2>&1; then
  git push origin "${BRANCH}"
else
  git push -u origin "${BRANCH}"
fi

echo
echo "Push complete."
