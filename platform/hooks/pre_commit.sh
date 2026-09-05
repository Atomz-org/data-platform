#!/usr/bin/env bash
# Pre-commit gate. Runs gate.yaml checks + impact analysis over staged changes.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
STAGED="$(git diff --cached --name-only --diff-filter=ACM)"
[ -z "$STAGED" ] && exit 0
cd "$ROOT"

# Ontology surfaces get their segregation suite before the gate: the layering
# (platform / group extension / project annotations) is cheap to verify here
# and expensive to discover broken in CI. ~1s, only when those paths change.
if echo "$STAGED" | grep -qE '^platform/src/pf/ontology/|^groups/[^/]+/ontology/|/contracts/annotations\.yaml$'; then
  uv run pytest platform/tests/test_ontology_segregation.py -q
fi

exec uv run pf gate --paths "$(echo "$STAGED" | tr '\n' ',')"
