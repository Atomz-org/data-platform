# Agentic Data Platform

Shared infrastructure (dlt · dbt · Dagster · DuckDB) plus a business-only project
per company. Sister companies run in parallel; Claude loads exactly one project's
context per session.

```
platform/          engines, ontology, knowledge graph, MCP, 14 skill toolkits   ← you never edit
groups/<g>/        a family of sister companies: ontology instance, shared macros
  projects/<p>/    one legal entity: sources, models, metrics                    ← you only edit here
vendor/            21 upstreams pinned as submodules, with recorded provenance   ← you never edit
data/_platform.duckdb   tracking DB (agent runs, spend, monitors, impact history)
```

## Quick start

```bash
uv sync
uv run pf ui                       # control plane → http://127.0.0.1:8787
uv run pf status                   # every group and project
```

## Daily commands

| Command | What it does |
|---|---|
| `pf new-group <g> --domain b2b_saas` | New company group (ontology instance, shared dbt package) |
| `pf new-project <g> <p>` | New entity inside a group |
| `pf new-project <g> <g>-rollup --rollup --sisters a,b` | Cross-entity roll-up project |
| `pf work <g> <p>` | Launch Claude scoped to exactly one project |
| `pf seed <g> <p>` | dlt → DuckDB → annotations → monitors → dbt → graph → card |
| `pf run-all <g>` | Every sister in parallel, then the roll-up |
| `pf impact <g> <p> <node>` | Blast radius. Exits 1 on breaking. **The merge gate.** |
| `pf check` | Ontology conformance across every project |
| `pf tokens` | Always-on token budget; fails if a card is over |
| `pf kg build/card/search/neighbors` | Knowledge graph operations |
| `pf vendor list/sync/drift/verify/why` | Vendored upstreams and their provenance |
| `pf pr report` | Blast radius, conformance and drift for the current change |
| `pf ui` / `pf mcp` | Dashboard / MCP server |

## What you write vs never touch

| You write, per project | You never touch |
|---|---|
| `src/<p>/sources/*.py` — annotated dlt sources | `platform/**` (engines, factories, toolkits, MCP) |
| `transform/models/**` — staging, marts, semantic | Dagster wiring, profiles, executors, pools |
| `CLAUDE.md` — rules the graph can't encode | `kg/*` — cards and graphs are generated |
| `groups/<g>/ontology/instance.yaml` | CI, engine pins, extension set |

Adding a sister company is `pf new-project`, sources and models. Upgrading dbt for
every entity is one line in `pyproject.toml`.

## The three mechanisms that make it work

**Ontology → everything.** Every dlt resource declares a concept, column roles and
links. Those annotations drive staging generation, PII policy, statistical
monitors, metric candidates, graph edges and conformance checks. `pf check` fails
on an unannotated or non-conforming source.

**Knowledge graph → retrieval, not grep.** `kg_search` / `kg_neighbors` / `kg_path`
let an agent route before it reads. The generated context card (~390 tokens) is the
always-in-context index; the full graph is queried on demand.

**Impact analysis → safety.** `pf impact` walks the graph downstream and names
every model, metric, dimension and exposure affected — plus the exposure owner.
Wire it into CI with `pf impact-gate`.

## Sister companies run genuinely in parallel

One DuckDB file per project (DuckDB's single-writer lock is per file), one Dagster
writer pool per project, and roll-ups that `ATTACH … (READ_ONLY)`. Sisters share
the group ontology, so `fct_revenue` has the same grain in both and the union is
safe by construction.

## Token budget

Constant regardless of how many groups, sisters or skills exist:

| Artefact | Budget | Actual |
|---|---:|---:|
| Project context card | 1500 | ~393 |
| Project CLAUDE.md | 600 | ~149 |
| Group card | 400 | ~136 |
| ROUTING.md | 400 | ~320 |
| **Session preamble** | | **~1000** |

`pf tokens` records these to the tracking DB and fails when one goes over.

## Adding a capability

Post-scaffold work lives in **one** ordered, idempotent list — `pf.scaffold.bootstrap.STEPS`.
`pf new-project` runs it; `pf bootstrap --all` re-runs it over every existing
project. Adding a platform capability means adding a step there, and both new and
old projects pick it up.

```bash
uv run pf bootstrap-steps          # what runs, and why each step exists
uv run pf bootstrap <g> <p>        # retrofit one project
uv run pf bootstrap --all          # retrofit everything after a platform upgrade
```

This exists because the steps used to be inlined in `new-project`: every
capability added afterwards — the PreToolUse hook, the dbt macro-paths, the
placeholder card — had to be hand-patched across existing projects, and each was
a silent hole until someone noticed.

## Loop engineering

Building blocks adapted from [loop-engineering](vendor/loop-engineering) (added as
a submodule): durable state, path gate, token budget, circuit breaker, ledger and
a readiness score. The loops themselves watch data-platform subjects.

```bash
uv run pf loop list                       # loops, autonomy levels, budgets
uv run pf loop run-all acme acme-us       # every L1 loop, then rewrite STATE.md
uv run pf loop audit                      # Loop Readiness Score (0-100)
uv run pf loop status                     # ledger
```

Governance files: `LOOP.md` (definitions) · `STATE.md` (generated) ·
`loop-constraints.md` (binding) · `gate.yaml` (path policy) · `loop-budget.md`.

**Three enforcement gates** make the impact check structural rather than a rule
an agent must remember:

| Gate | Fires | Effect |
|---|---|---|
| `pf check` | on demand / CI | blast radius of every working-tree change |
| pre-commit hook | `git commit` | blocks a breaking change; `--no-verify` to override with a reason |
| PreToolUse hook | before any Edit/Write | denies secrets and generated files; prints blast radius for models |

## Skill toolkits

14 plugins in `platform/toolkits`, referenced by every project and copied into
none. Ported from dltHub AI Workbench, dbt-labs/dbt-agent-skills,
duckdb/duckdb-skills and dagster-io/skills, adapted for dlt Core / dbt Core.
`ROUTING.md` resolves their overlaps: graph → metrics → ad-hoc SQL, in that order.

## Vendored upstreams

Twenty-one upstreams are pinned as branch-tracked submodules under `vendor/`, and every
borrowing is written down as a **path pair** — one file upstream, one or more of
ours — in `platform/src/pf/vendor/registry.yaml`. 53 adoptions, 22 explicit
declines. Full account: [`docs/VENDOR.md`](docs/VENDOR.md); the agent-loadable
index is [`docs/VENDOR-CARD.md`](docs/VENDOR-CARD.md) (~420 tokens). Both are
generated from the registry.

| Command | What it does |
|---|---|
| `pf vendor list [-v]` | Every upstream, licence, pinned commit, reviewed state |
| `pf vendor sync` | Fetch each tracking branch, then report what it means for us |
| `pf vendor drift` | What moved since a human last looked — local, never fetches |
| `pf vendor approve <id>` | Record the current checkout as reviewed |
| `pf vendor verify` | Declared paths still exist; schema contracts still hold |
| `pf vendor why <file>` | Where a file of ours came from, and what we changed |
| `pf vendor licences` | Licences, and the two that constrain how this ships |

**`vendor.lock.json` is not the submodule pointer.** The gitlink records which
commit is checked out; the lock records which commit a person *reviewed*, plus a
git OID per adopted path. Those diverge the moment someone runs
`--remote` without reading anything, and that gap is what makes drift observable.
An upstream that moved forty commits without touching anything we adopted is a
free fast-forward; one that touched `core/wren-mdl/mdl.schema.json` names
`projections/mdl.py` and stops.

Three of the pins are **executable contracts**, checked by `pf vendor verify`:

| Vendored file | Checks |
|---|---|
| `opentopology/schemas/otop-core-v0.2.schema.json` | `pf semantic otop` output |
| `wrenai/core/wren-mdl/mdl.schema.json` | `pf semantic mdl` output |
| `loop-engineering/patterns/registry.schema.json` | field parity with `LoopSpec` |

Sync runs weekly in CI and opens a PR; it never approves, because approval means
a human read the diff.

## Pull requests

`pf pr report` assembles what a reviewer would otherwise rebuild by hand: per
project, the blast radius with exposure owners, conformance and readiness;
repo-wide, path-gate verdicts and vendor drift; then one verdict — **block /
review / clear**. `clear` means nothing downstream breaks and no gate fired. It
is not an approval.

The report is written to `data/pr/<n>.json` and posted as a single PR comment
that is edited in place. `pf ui` reads the same JSON, so the dashboard shows the
verdict CI computed rather than a second opinion.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Attribution for adapted
third-party material is in [NOTICE](NOTICE) and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md); the per-path provenance
record is `platform/src/pf/vendor/registry.yaml` (`pf vendor why <file>`).
Upstreams under `vendor/` are submodule pointers and keep their own licenses.

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Security
reports go through [SECURITY.md](SECURITY.md), not the issue tracker.
