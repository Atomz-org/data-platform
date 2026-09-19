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
  log "openmetadata ${PF_OM_VERSION:-?} migrate"
  ( cd /opt/openmetadata && ./bootstrap/openmetadata-ops.sh migrate ) 2>&1 | tail -5
fi

# The half of an upgrade that `migrate` does not do. Entity rows live in
# Postgres; the search index is a projection of them in Elasticsearch, and a
# release that changes an index mapping leaves search returning stale shapes —
# or nothing — while every table is still perfectly present in the catalogue.
# That is a confusing failure to meet cold, so it gets a switch rather than a
# runbook step to remember.
#
# Off by default: this reads every entity and rewrites the index, which is
# minutes on a real catalogue and pure waste on an ordinary restart.
#
#   PF_OM_REINDEX=1         rebuild only where the mapping actually changed
#   PF_OM_REINDEX=force     rebuild regardless — after a restore, or when the
#                           index and the database have drifted for any reason
#   PF_OM_REINDEX=recreate  drop the indexes first. The heaviest option and the
#                           safe one across a major version, since Postgres
#                           remains the source of truth either way.
#
# Before supervisord, not after: reindexing under a serving server would have
# the UI answering searches from an index being rewritten underneath it.
case "${PF_OM_REINDEX:-}" in
  "") ;;
  1|true|yes)  om_reindex_args="--auto-tune" ;;
  force)       om_reindex_args="--auto-tune --force" ;;
  recreate)    om_reindex_args="--auto-tune --force --recreate-indexes" ;;
  *)
    echo "PF_OM_REINDEX=${PF_OM_REINDEX} is not one of 1|force|recreate" >&2
    exit 1
    ;;
esac

if [ -n "${om_reindex_args:-}" ]; then
  log "openmetadata reindex ${om_reindex_args}"
  # Said plainly because it is the surprising part: nothing in this container is
  # serving yet, so Dagster and the review servers are down for the duration
  # too, not just the catalogue. That is the price of not racing OpenMetadata's
  # own index bootstrap, and it is why this is off by default.
  echo "    the whole stack stays down until this finishes"
  # Not fatal. A failed reindex is a degraded search over an intact catalogue,
  # and refusing to start the stack over it would turn a partial outage into a
  # total one. It is loud in the log and `pf stack status` reports the version
  # that is actually serving.
  if ! ( cd /opt/openmetadata \
         && ./bootstrap/openmetadata-ops.sh reindex ${om_reindex_args} ) 2>&1 \
       | tail -15; then
    echo "!! reindex failed — the catalogue is intact, search may be stale." \
         "Re-run with: podman exec pf_stack bash -c" \
         "'cd /opt/openmetadata && ./bootstrap/openmetadata-ops.sh reindex --auto-tune --force'" >&2
  fi
fi

# ---------------------------------------------------------- catalogue auth --
# `catalog_sync` publishes the ontology, the glossary and every table to the
# server in this same container, and it authenticates with the ingestion bot's
# JWT. OpenMetadata's documented way to obtain that is to open the UI and copy
# it out of Settings → Bots, which is how eight Dagster code locations ended up
# failing with "OPENMETADATA_JWT_TOKEN is not set" against a catalogue eighty
# milliseconds away.
#
# Here the token does not need carrying: same database, same FERNET_KEY. Resolve
# it once and export it, so every process supervisord starts inherits it.
# Exported rather than written anywhere — it lives in the process environment
# for the life of the container and nowhere else.
#
# After the migrations above, deliberately: OpenMetadata creates the bot on its
# first migration, so resolving earlier finds nothing on a fresh database.
if [ -z "${OPENMETADATA_JWT_TOKEN:-}" ] && [ -n "${PF_STACK_PG_HOST:-}" ]; then
  if OPENMETADATA_JWT_TOKEN="$(uv run pf stack token 2>/dev/null)" \
     && [ -n "$OPENMETADATA_JWT_TOKEN" ]; then
    export OPENMETADATA_JWT_TOKEN
    log "catalogue auth resolved from the database"
  else
    unset OPENMETADATA_JWT_TOKEN
    # Not fatal. Everything except publishing to the catalogue works without
    # it, and stopping the stack over one asset would be the wrong trade.
    echo "!! could not resolve the ingestion-bot token — catalog_sync will" \
         "fail to publish. Diagnose with: podman exec pf_stack" \
         "bash -c 'cd \"\$PF_REPO\" && uv run pf stack status'" >&2
  fi
fi

log "supervisord"
exec /usr/bin/supervisord -c "$REPO/platform/stack/supervisord.conf"
