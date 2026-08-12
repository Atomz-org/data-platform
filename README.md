# Agentic Data Platform

Shared infrastructure (dlt · dbt · Dagster · DuckDB) plus a business-only project
per company. Sister companies run in parallel; Claude loads exactly one project's
context per session.

```
platform/          engines, ontology, knowledge graph, MCP, 13 skill toolkits   ← you never edit
groups/<g>/        a family of sister companies: ontology instance, shared macros
  projects/<p>/    one legal entity: sources, models, metrics                    ← you only edit here
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

## Skill toolkits

13 plugins in `platform/toolkits`, referenced by every project and copied into
none. Ported from dltHub AI Workbench, dbt-labs/dbt-agent-skills,
duckdb/duckdb-skills and dagster-io/skills, adapted for dlt Core / dbt Core.
`ROUTING.md` resolves their overlaps: graph → metrics → ad-hoc SQL, in that order.
