#!/usr/bin/env bash
# Bring the control plane up in dependency order, then hand off to supervisord.
#
# Everything here is ordered by what *cannot* be retried. supervisord restarts a
# process that dies, so a slow start is not a problem: nginx answering 502 for
# ten seconds while OpenMetadata boots is fine. What is not fine is a schema
# that does not exist when Dagster first connects, or a workspace file whose
# absolute paths point somewhere this container cannot see — those fail once,
# permanently, and look like application bugs.
#
# So: wait for Postgres, create the schema, regenerate the config from the
# roster that is actually mounted, migrate both products, and only then start
# anything. Render before migrate, not after: the storage block `pf stack
# render` writes is what tells `dagster instance migrate` which database to
# migrate, and in the other order it cheerfully migrates the SQLite file.
set -euo pipefail

REPO="${PF_REPO:-$PWD}"
cd "$REPO"

log() { printf '==> %s\n' "$*"; }

if [ ! -f uv.lock ]; then
  echo "no uv.lock at $REPO — is the repository mounted at the path it was" \
       "built for? workspace.yaml holds absolute paths and will not match." >&2
  exit 1
fi

: "${DAGSTER_HOME:=$REPO/.dagster}"
export DAGSTER_HOME
mkdir -p "$DAGSTER_HOME"

# ---------------------------------------------------------------- python --
# Resolved against the mounted repo's lockfile rather than baked at build time,
# for the reason Containerfile.dagster gives: a baked environment disagrees with
# the host the moment a dependency changes, which is the drift a container is
# supposed to remove.
log "uv sync"
uv sync --extra recce --extra artifacts --extra stack --frozen 2>&1 | tail -3

# -------------------------------------------------------------- postgres --
if [ -n "${PF_STACK_PG_HOST:-}" ]; then
  log "waiting for postgres at ${PF_STACK_PG_HOST}:${PF_STACK_PG_PORT:-5432}"
  probe="import os,socket;socket.create_connection((os.environ['PF_STACK_PG_HOST'],int(os.environ.get('PF_STACK_PG_PORT') or 5432)),timeout=2)"
  tries=0
  until uv run python -c "$probe" 2>/dev/null; do
    tries=$((tries + 1))
    if [ "$tries" -ge 60 ]; then
      echo "postgres never accepted a connection" >&2
      exit 1
    fi
    sleep 2
  done

  # One database, two schemas. Idempotent, and it needs the admin role: Dagster's
  # own role cannot create a schema and should not be able to, since that is what
  # keeps its migrations out of OpenMetadata's tables.
  log "pf stack db-init"
  uv run pf stack db-init
fi

# ------------------------------------------------------------- generated --
# Derived from the project roster in the mount, so regenerated on every start
# rather than trusted from git: a sister added on the host since the last render
# would otherwise have no code location and no review server, and nothing would
# report that.
log "pf dagster-workspace"
uv run pf dagster-workspace

log "pf stack render"
uv run pf stack render

# ------------------------------------------------------------- migrations --
if [ -n "${PF_STACK_PG_HOST:-}" ]; then
  # Dagster does create its tables lazily on first use, but lazily means "inside
  # the first webserver request", and a failed migration there surfaces as a 500
  # on the asset graph rather than as a startup error anyone will read.
  log "dagster instance migrate"
  uv run dagster instance migrate 2>&1 | tail -5
fi

# Idempotent: a database already at this version is a no-op. Skippable because a
# second stack pointed at the same database must not race the first one.
if [ "${PF_OM_MIGRATE:-1}" = "1" ]; then
  log "openmetadata migrate"
  ( cd /opt/openmetadata && ./bootstrap/openmetadata-ops.sh migrate ) 2>&1 | tail -5
fi

log "supervisord"
exec /usr/bin/supervisord -c "$REPO/platform/stack/supervisord.conf"
