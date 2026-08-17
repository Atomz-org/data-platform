# The control plane

Three products — OpenMetadata, Dagster and recce — on one database, one origin
and one image.

```
                    http://localhost:8080
                            │
                   ┌────────┴────────┐
                   │      nginx      │
                   └────────┬────────┘
        /                   /dagster/            /recce/<project>
        │                       │                        │
  OpenMetadata            dagster-webserver          recce server
    :8585                     :3000                  :8100…8107
        │                       │                        │
        │              8 × code-server                   │
        │                :4000…4007                      │
        └───────────┬───────────┘                        │
                    │                          (state lives in R2,
        openmetadata_db @ :5432                 not in a database)
        ├── public    OpenMetadata, 176 tables
        └── dagster   Dagster, 22 tables
```

Everything above the database line runs in **one container**, `pf_stack`, from
one image. Postgres and Elasticsearch are their own containers: they are
stateful, they have their own upgrade cycles, and folding a database into an
application image is how you lose the database.

## Run it

```bash
PF_REPO="$PWD" podman compose -f platform/deploy/compose.yaml up -d --build
```

`PF_REPO` is required and it must be the repository root. The repo is
bind-mounted into the container **at its host path**, because Dagster's
workspace holds absolute `working_directory` entries — mount it anywhere else
and every code location loads zero assets while reporting no error.

Then:

| URL | What |
|---|---|
| `http://localhost:8080/pf/` | the launcher — every project, all three links |
| `http://localhost:8080/` | OpenMetadata |
| `http://localhost:8080/dagster/` | Dagster |
| `http://localhost:8080/recce/<project>` | that project's review |
| `http://localhost:8585` | OpenMetadata direct, for `metadata ingest` |
| `http://localhost:3000/dagster/` | Dagster direct, for `dagster` CLI clients |

Note the path on 3000: the webserver runs with `--path-prefix /dagster` so that
nginx can pass the prefix through unchanged, which means its *own* port serves
under that path too. `http://localhost:3000/` is a 404, not a broken Dagster.

The recce servers are **not** published. They bind the container's loopback and
are reached through the front door, which is what makes one origin possible;
`pf stack status` probes them there rather than on their own ports.

`pf stack status` reports what is configured and what is actually answering.

## One database, two schemas

`openmetadata_db` holds both products, separated by schema rather than by
server:

- `public` — OpenMetadata's ~176 tables. Untouched; it was there first and its
  Flyway migrations assume they own it.
- `dagster` — runs, event logs, schedules, ticks. Owned by a `dagster` role
  with no rights in `public`.

Dagster has no schema setting. It has `params`, which are urlencoded onto the
libpq connection string, and libpq accepts `options`:

```
postgresql://dagster:…@postgresql:5432/openmetadata_db?options=-c%20search_path%3Ddagster
```

That one parameter is what keeps the two products apart, and dropping it does
not fail — Dagster's migrations run happily against `public`, interleaving its
tables with OpenMetadata's, and the damage only shows at the next OpenMetadata
upgrade. `pf stack render` writes it; `pf stack status` shows the table counts
per schema so a drift is visible rather than inferred.

Recce gets no schema. It has no server-side database at all: a review is a
`recce_state.json`, and since `pf artifacts` those live in R2 (`docs/ARTIFACTS.md`).

### Environment

| Variable | Default | Used by |
|---|---|---|
| `PF_STACK_PG_HOST` | *(unset)* | **the switch.** Unset ⇒ SQLite, as before |
| `PF_STACK_PG_PORT` | `5432` | Dagster |
| `PF_STACK_PG_DB` | `openmetadata_db` | Dagster |
| `PF_STACK_PG_USER` | `dagster` | Dagster |
| `PF_STACK_PG_PASSWORD` | *(none)* | Dagster |
| `PF_STACK_PG_SCHEMA` | `dagster` | Dagster |
| `PF_STACK_PG_ADMIN_USER` | `postgres` | `pf stack db-init` only |
| `PF_STACK_PG_ADMIN_PASSWORD` | *(none)* | `pf stack db-init` only |

`dagster.yaml` refers to these **by name**, never by value, so the tracked file
never carries a password.

Unset `PF_STACK_PG_HOST` is not an error. A laptop with no stack running keeps
its SQLite instance, and `pf stack render` removes the storage block rather than
writing one that points at a host nobody is serving — a `dagster.yaml` naming an
unreachable Postgres fails at *import*, taking every code location down with it.

To point host-side `dagster dev` at the same database, set `PF_STACK_PG_HOST=127.0.0.1`
(compose publishes 5432 on loopback) and re-run `pf stack render`.

## One origin, two root-anchored SPAs

OpenMetadata's UI and recce's UI both fetch their bundles from `/` and both call
an API under `/api`. Serving recce at `/recce/<project>/` behind a path-prefixed
proxy **does not work**: its frontend is a Next.js static export built with no
`basePath`, so its HTML asks for `/_next/…` regardless of what path served it,
and its client router matches `window.location.pathname` against routes that all
start at `/`. Landing on a prefix renders its 404. The clean fix is rebuilding
the bundle with a basePath, and that bundle is vendored.

So the merge happens on paths, and the two apps turn out not to overlap:

```
/api/v1/…    OpenMetadata's REST API — its only API prefix
/api/…       recce's REST API and websocket — never versioned
/_next/  /logo/  /imgs/            recce's assets
/lineage /checks /query /404       recce's pages
/dagster/…   Dagster, which supports --path-prefix natively
everything else                    OpenMetadata
```

`^~` on `/api/v1/` makes it beat `/api/` regardless of block ordering. That is
the one rule holding the two APIs apart.

**Which project's recce.** One recce process serves one project, so the shared
root routes need a subject. `/recce/<project>` sets a `pf_recce` cookie and
redirects to `/lineage`; an nginx `map` turns that cookie into a port. One
project is in view at a time, which is what a review *is*.

**The bar.** Both apps get a small fixed navigation bar injected by `sub_filter`,
loading `/pf/bar.css` and `/pf/bar.js` rather than inline markup — OpenMetadata
sends a Content-Security-Policy, and an inline script would be dropped on
exactly one of the two apps.

**Costs, stated.** `/lineage`, `/checks` and `/query` at the root now belong to
recce, so if OpenMetadata ever adds a root route by those names it becomes
unreachable here. `/favicon.ico` is OpenMetadata's, so recce pages show the
catalogue's icon.

## Processes

`platform/stack/supervisord.conf` is generated by `pf stack render` from the
project roster. Per project it declares one Dagster code server and one recce
server; plus OpenMetadata, dagster-webserver, dagster-daemon and nginx.

Two decisions there are load-bearing on an 8 GB machine:

**Code servers are standalone.** A `python_module` entry in `workspace.yaml` is
not a shared service: the webserver forks its own gRPC child per location and
the daemon forks a *second*, so eight projects became nineteen Python processes
holding 3.1 GB — enough to squeeze Elasticsearch until it refused connections
and Postgres until it dropped OpenMetadata's. `grpc_server` entries point both
at one process each. It also means reloading one project no longer restarts the
other seven.

**Recce servers start only where there is a review.** A recce process is ~350 MB
of dbt manifest whether or not it has anything to show. The rest stay declared
and stopped; the front door serves an explanatory page instead of a 502, and one
command starts one:

```bash
podman exec pf_stack supervisorctl \
  -c "$PWD/platform/stack/supervisord.conf" start recce-<project>
```

Everything under `platform/stack/` is generated and gitignored — it carries
absolute host paths, and the entrypoint regenerates it on every start.

## The image

`platform/Containerfile.stack`, ~880 MB.

The obvious build is `FROM openmetadata/server`. That image is Alpine, so musl,
and the wheels this platform needs — duckdb, pydantic-core, psycopg2 — publish
manylinux and not musllinux; adding Python to it means compiling them, Rust
toolchain included. The other direction is cheap: `/opt/openmetadata` is jars,
shell scripts and YAML, none of it libc-linked, so it copies onto a glibc base
unchanged. The JRE cannot be copied from that image for the same musl reason and
comes from Temurin's jammy build — glibc 2.35, older than bookworm's 2.36, which
is the direction that works.

Python dependencies are **not** baked. They are resolved at start against the
mounted repo's `uv.lock`, so the container and the developer who mounted it run
the same code.

`MALLOC_ARENA_MAX=2` is set: ten-odd threaded Python processes in one container
otherwise accumulate per-thread glibc arenas that are never returned, and RSS
tracks thread count rather than live data.

## Startup order

The entrypoint does what cannot be retried, then hands off to supervisord, which
restarts what can:

1. `uv sync` against the mounted lockfile
2. wait for Postgres
3. `pf stack db-init` — the role and the schema, idempotent, as admin
4. `pf dagster-workspace` and `pf stack render`
5. `dagster instance migrate`, then OpenMetadata's `migrate`
6. `supervisord`

Render before migrate, not after: the storage block `pf stack render` writes is
what tells `dagster instance migrate` which database to migrate, and in the
other order it cheerfully migrates the SQLite file.

`PF_OM_MIGRATE=0` skips step 5's second half, for when a second stack must not
race the first one's migration.

## Upgrading

**Dagster** is a lockfile change and a restart. Its packages are resolved at
container start against the mounted `uv.lock`, not baked into the image:

```bash
uv lock --upgrade-package dagster --upgrade-package dagster-webserver \
        --upgrade-package dagster-dbt --upgrade-package dagster-postgres
podman restart pf_stack
```

`dagster instance migrate` runs on every start, so the schema follows. They must
move as a set — `dagster-postgres` uses the library numbering, so 0.29.x pairs
with core 1.13.x — and uv resolves one version per package across the whole
workspace, which is where a bump actually fails. Storage migrations are one-way;
`pg_dump -n dagster` first, and `DROP SCHEMA dagster CASCADE` is the rollback
that costs run history and touches nothing of OpenMetadata's.

**OpenMetadata** is one build argument:

```bash
OM_VERSION=1.14.0 PF_OM_REINDEX=1 PF_REPO="$PWD" \
  podman compose -f platform/deploy/compose.yaml up -d --build
```

The distribution is pulled by tag and copied, so no line of the Containerfile
changes. The built version is recorded as `PF_OM_VERSION` and as the
`io.openmetadata.version` label, and `pf stack status` reports the version that
is actually *answering* — an upgrade that failed to take otherwise leaves the
previous distribution running and reporting nothing wrong.

### `PF_OM_REINDEX`

`migrate` moves the tables. The search index is a separate projection of them in
Elasticsearch, and a release that changes an index mapping leaves search
returning stale shapes — or nothing — while every table is still perfectly
present. Hence the switch:

| Value | What it does |
|---|---|
| *(unset)* | nothing. The default, because this is minutes of work on an ordinary restart |
| `1` | rebuild only where the mapping actually changed |
| `force` | rebuild regardless — after a restore, or when index and database have drifted |
| `recreate` | drop the indexes first. The safe option across a major version |

It runs **before** anything starts serving, so the whole container — Dagster and
the review servers included, not just the catalogue — is down for the duration.
That is deliberate: it avoids racing OpenMetadata's own index bootstrap. Set it
on the upgrade run and leave it unset otherwise. OpenMetadata builds into
`*_rebuild_*` indices and swaps aliases atomically, so an interrupted reindex
leaves the old index serving rather than a half-built one.

### What a bump deliberately does not carry

- **Postgres.** Pinned separately as `PF_POSTGRES_IMAGE`, currently PostgreSQL
  15.18. getcollate publishes a postgresql image per release, and following that
  tag is how a Postgres 16 server meets a 15 data directory and refuses to
  start — now taking Dagster's run history with it, since they share the
  instance. Move it deliberately, with a dump and restore.
- **Elasticsearch.** `PF_ES_IMAGE`. This one may genuinely need to move *with*
  an upgrade, since OpenMetadata constrains which majors it will talk to. Change
  it and the index together: `PF_OM_REINDEX=recreate` on the first run after.
- **`FERNET_KEY`.** Must not change, or every stored service connection silently
  fails to decrypt.

## Volumes

The compose file declares both volumes `external: true` under the names the
previous hand-started stack wrote:

```
openmetadata_openmetadata_db_data
openmetadata_es-data
```

A compose project that declared its own would silently start on an empty
database, and the first sign would be an empty catalogue. `external` fails
loudly instead. On a fresh machine, create them first:

```bash
podman volume create openmetadata_openmetadata_db_data
podman volume create openmetadata_es-data
```

## `FERNET_KEY`

OpenMetadata encrypts stored service credentials with it. It must match whatever
wrote the rows already in the database; a fresh key does not error, it silently
fails to decrypt every stored connection. The image pins OpenMetadata's own
published compose default, which is what the existing volume was written with.
Change it only alongside a re-encryption.
