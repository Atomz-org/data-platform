#!/usr/bin/env bash
# Sync against the mounted repo, then serve.
#
# The sync happens here rather than at build time on purpose: the repo is a bind
# mount, so its uv.lock is whatever the host has *now*. Resolving at build time
# would pin the image to a lockfile that the host has since moved past, and the
# container would run different code from the developer who mounted it.
set -euo pipefail

REPO="${PF_REPO:-$PWD}"
cd "$REPO"

if [ ! -f uv.lock ]; then
  echo "no uv.lock at $REPO — is the repository mounted at the path it was built for?" >&2
  exit 1
fi

# Regenerate the workspace before serving. Its working_directory entries are
# absolute host paths; if the mount path does not match them, Dagster loads no
# code locations and reports nothing wrong. Regenerating makes them match
# whatever this container actually sees.
echo "==> uv sync"
uv sync --extra recce --extra artifacts --frozen 2>&1 | tail -3

echo "==> workspace"
uv run pf dagster-workspace

mkdir -p "${DAGSTER_HOME:?}"
echo "==> dagster dev on 0.0.0.0:3000"
exec uv run dagster dev -w platform/workspace.yaml -h 0.0.0.0 -p 3000 "$@"
