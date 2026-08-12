#!/usr/bin/env bash
# Pre-commit gate. Runs gate.yaml checks + impact analysis over staged changes.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
STAGED="$(git diff --cached --name-only --diff-filter=ACM)"
[ -z "$STAGED" ] && exit 0
cd "$ROOT"
exec uv run pf gate --paths "$(echo "$STAGED" | tr '\n' ',')"
