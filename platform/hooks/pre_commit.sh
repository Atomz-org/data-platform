#!/usr/bin/env bash
# Pre-commit gate. Runs gate.yaml checks + impact analysis over staged changes.
#
# The filter is load-bearing. `ACM` — Added, Copied, Modified — silently drops
# renames, so `git mv` past the gate was free: a commit moving any number of
# files reported "0 path(s)" and every rule was skipped, including the maxFiles
# cap and the denylist. Renaming a denied path is still touching it, and moving
# a dbt model changes its node id, which is exactly what impact analysis exists
# to catch. `R` emits the destination path, which is the one to judge.
#
# `D` is deliberately still absent. Including it would deny *deleting* a
# denylisted file as well as editing one, which is a policy change rather than a
# bug fix — see the note in gate.yaml.
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
STAGED="$(git diff --cached --name-only --diff-filter=ACMR)"
[ -z "$STAGED" ] && exit 0
cd "$ROOT"
exec uv run pf gate --paths "$(echo "$STAGED" | tr '\n' ',')"
