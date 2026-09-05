# Blueprint

The architecture of this repository: what each layer is, why it is shaped that
way, and where the seams are. This is the map; the per-subsystem references it
points at (`docs/*.md`) are the territory.

## What this is

A **multi-tenant agentic data platform**. One shared engine layer serves many
companies, each company's business logic is isolated in its own project, and
every action an agent takes against the platform is gated before and recorded
after. The organising principle appears in every layer:

> **Infra is shared; business logic is not.**

Three corollaries carry most of the design:

1. **Ontology → everything.** A dlt source declares its concept, column roles
   and links once; staging models, PII policy, statistical monitors, metric
   candidates, graph edges and conformance checks are all derived from that
   declaration. Nothing semantic is written twice.
2. **Retrieval, not grep.** A knowledge graph per project (`kg_search`,
   `kg_neighbors`, `kg_path`) and a ~400-token generated context card let an
   agent route before it reads. The session preamble stays ~1000 tokens no
   matter how many groups exist.
3. **Controls are named, not asserted; actions are recorded, not assumed.**
   Governance is enforced by artefacts that resolve (`pf air coverage`) and a
   hash-chained provenance ledger the agent cannot edit — not by instructions
   an agent is trusted to remember.

## Map of the repository

```
platform/                     shared engine layer — the `pf` package, toolkits,
                              control-plane deploy. Never edited from a project session.
groups/<group>/               a family of sister companies: shared ontology instance,
                              shared dbt macros, group tools.yaml, group air.yaml
  projects/<project>/         one legal entity: own warehouse, own dlt sources,
                              own dbt project, own projections
vendor/                       pinned upstreams as read-only submodules (Recce family
                              grouped under vendor/recce/)
provenance/                   the action ledger — written by hooks and pf.provenance,
                              denied to every agent's Edit/Write
data/_platform.duckdb         tracking DB: agent runs, spend, monitors, token budgets,
                              impact history, PR reports (data/pr/<n>.json)
docs/                         the reference docs this blueprint indexes
gate.yaml                     machine-readable safety policy (hand-maintained);
                              gate.capabilities.yaml is the generated half, merged at load
LOOP.md · STATE.md ·          loop-engineering governance: definitions, generated state,
loop-constraints.md ·         binding constraints, budget, ledger
loop-budget.md · loop-ledger.json
```

Current tenancy: five groups (`acme`, `globex`, `hospital`, `jaffle`,
`zenith`), nine projects. `jaffle/jaffle-shop` is the reference
implementation — every platform capability is proven there first.

## Layer 1 — `platform/`: the engine

One Python package, `pf` (`platform/src/pf/`), exposing one CLI (`uv run pf`),
one MCP server, and one Dagster workspace. Subpackage map:

| Subpackage | Owns |
|---|---|
| `runtime/` | how anything talks to a warehouse: `warehouse.py` (the connect seam), `adbc.py` (ADBC/Arrow driver), `quack.py` (dev serving), `targets.py` (warehouse menu + dbt profiles), `dbt_runtime.py` / `dlt_runtime.py` / `dagster_runtime.py` / `staging.py` |
| `scaffold/` | `generator.py` (what `pf new-group` / `pf new-project` write) and `bootstrap.py` (the STEPS list — see [Extension seams](#extension-seams)) |
| `ontology/` | concept classes, annotation model, conformance checks, `policy.yaml` (the named-control register) |
| `kg/` | knowledge-graph build, context cards, search/neighbors/path |
| `provenance/` | the five-stage action ledger and its verification |
| `air/` | FINOS AI-governance crosswalk: coverage derivation and the per-entity merge gate |
| `governance/` | OpenTopology (`otop.json`) constraint traceability per project |
| `projections/` | one semantic layer projected many ways: Evidence BI sites, WrenAI MDL, OpenMetadata catalogue payloads |
| `tools/` | the Tool framework (`spec.py`, `registry.py`, `config.py`) and the tools themselves: recce, elementary, expectations, wren, openmetadata, dbtproject |
| `agents/` | LLM-call base that writes provenance for model invocations |
| `loops/` | loop-engineering runtime: durable state, path gate, budgets, circuit breaker, readiness score |
| `mcp/` | the `pf` MCP server (`kg_*`, `impact_analysis`, `dbt_*`, metrics, secrets — see `docs/CLAUDE-CODE.md`) |
| `stack/` · `ui/` | control-plane render/status and the `pf ui` dashboard (:8787) |
| `vendor/` | `registry.yaml`, the per-path borrowing ledger behind `pf vendor why` |
| `evals/` · `housekeeping/` · `onboard/` | eval generation, lakehouse/Dagster maintenance, project onboarding |

`platform/toolkits/` holds **21 Claude Code plugins** (dbt-modeling,
dlt-ingest, duckdb-ops, recce-review, evidence-bi, power-tools, …) referenced
by every project and copied into none; `platform/toolkits/ROUTING.md` resolves
their overlaps (graph → metrics → ad-hoc SQL, in that order). Optional tools
install as pyproject extras so the base checkout stays light and a missing tool
degrades to "not installed" (`pf tool doctor` reports the gap) — with one
deliberate isolation: elementary's CLI installs outside the workspace because
its posthog pin conflicts with recce's.

## Layer 2 — `groups/` and `projects/`: the tenants

A **group** is a family of sister companies. It owns what must be conformed
across them and nothing else:

```
groups/<g>/
  ontology/instance.yaml     the group's ontology instance — same grain law for every sister
  shared/                    shared dbt macros
  kg/ · evals/               group-level card and evals
  tools.yaml                 tools every sister inherits
  air.yaml                   controls the group commits to (pf air gate enforces)
  CLAUDE.md                  group rules the graph can't encode
```

A **project** is one legal entity, and its directory is the complete anatomy
of a tenant:

```
groups/<g>/projects/<p>/
  src/<p>/sources/*.py       annotated dlt sources — the single semantic declaration
  transform/                 the dbt project: generated staging, hand-written marts,
                             MetricFlow semantic models
  data/                      the warehouse: <p>.duckdb (denied to agents),
                             <p>.quack.json dev-server state (denied and gitignored)
  reporting/                 generated Evidence BI site
  mdl/mdl.json               generated WrenAI MDL — the external semantic contract
  catalog/                   generated OpenMetadata ingestion workflows
  governance/otop.json       generated OpenTopology constraint chain
  kg/                        generated graph + context card
  contracts/ · decisions/ · docs/ · evals/ · .memory/
  air.yaml · tools.yaml · CLAUDE.md · pyproject.toml
```

Isolation is physical, not conventional: one DuckDB file per project (the
single-writer lock is per file), one Dagster code location per project
(`platform/workspace.yaml`, generated — a reload in one sister never touches
another), one Dagster writer pool per project. Roll-up projects
(`pf new-project <g> <g>-rollup --rollup`) `ATTACH … (READ_ONLY)` their
sisters; the union is safe because the group ontology forced the same grain on
both sides. **Never read another group or another sister project** — business
logic carried across entities is a bug, not a shortcut.

## Layer 3 — `vendor/`: pinned upstreams with recorded provenance

Twenty-two submodule paths (the Recce family grouped under `vendor/recce/`),
**read-only always**. Every borrowing is a recorded path pair in
`platform/src/pf/vendor/registry.yaml` — one file upstream, one or more of
ours — queryable with `pf vendor why <file>`. `vendor.lock.json` records which
commit a *human reviewed* (distinct from the gitlink, which records what is
checked out); the gap between them is what makes drift observable. Several
pins are executable contracts — our generated output is validated against the
vendored schema file, not against memory (`pf vendor verify`). Bumping a pin
is a human decision, never an agent's. Index: `docs/VENDOR-CARD.md`; full
account: `docs/VENDOR.md`.

## The data path

One project, end to end (`pf seed <g> <p>` runs the whole chain):

```
annotated dlt sources ──▶ DuckDB (dev) / warehouse (prod)
        │                        │
        │ annotations            ▼
        ├──▶ generated staging   dbt build ──▶ marts ──▶ MetricFlow semantic layer
        ├──▶ PII policy / monitors                          │
        └──▶ graph edges                                    ▼
                                              projections, all generated:
                                              · Evidence BI site   (reporting/)
                                              · WrenAI MDL         (mdl/mdl.json)
                                              · OpenMetadata       (catalog/)
                                              · OpenTopology       (governance/otop.json)
                                              · knowledge graph    (kg/)
```

Dagster orchestrates it asset-first (`@dbt_assets` makes lineage cross the
dlt/dbt boundary); `pf run-all <g>` runs every sister in parallel, then the
roll-up. The projections are all *generated from the same semantic layer* —
BI, the external MDL contract, the catalogue and the constraint chain are four
views of one declaration, which is why hand-editing any of them is denied or
pointless (the next regeneration wins).

## Dev and prod are different protocols, deliberately

**Dev: duckdb-quack serving, ADBC/Arrow everywhere.** Every project's dev
DuckDB is served by a `duckdb-quack` server (`pf quack serve|status|stop`,
`pf.runtime.quack`), not opened as a bare file:

- **The wire is read-only, enforced twice.** The server holds the database
  `read_only=True` — the engine refuses writes over the wire — and the client
  independently refuses non-read statements before the network hop using
  DuckDB's real parser (`extract_statements`), which catches what prefix
  matching cannot (`WITH … INSERT`, multi-statement smuggling, `CALL`, `COPY`).
- **Writers take a write window.** dbt, dlt, MetricFlow, elementary and recce
  runs are wrapped in `quack.write_window`: server stops, the writer gets the
  plain file, the server returns. There is no write path over the network.
- **localhost only, token never leaves the machine.** The host is not a
  parameter; the per-server token lives in a 0600 state file that is
  gitignored *and* gate-denied, and the CLI prints it redacted.
- **Custody is recorded.** Serve, stop and every window borrow are full
  provenance actions — "who held the warehouse when" is a ledger query.
- **All pf↔DuckDB communication rides ADBC/Arrow** (`pf.runtime.adbc`, driver
  loaded from the DuckDB wheel's own `duckdb_adbc_init`) — Arrow record
  batches across every boundary, engine-level `read_only` where reads are the
  contract.

Each project carries a generated `docs/quack.md` runbook; the four guardrails
are named policies in `platform/src/pf/ontology/policy.yaml` and resolve under
`pf air coverage`.

**Prod: a per-entity warehouse menu.** `pf.runtime.targets` keeps the full
registry — DuckLake (the default for new projects), Snowflake, BigQuery,
ClickHouse and others — and each entity picks in its dbt profile. Dev-on-quack
is platform-wide; the prod warehouse is a business decision per entity.
jaffle-shop is the DuckLake proof (`ducklake:` metadata catalog, full build
green end to end); the zenith/acme sisters illustrate the menu staying open.

## The governance spine

Four mechanisms, layered so that none depends on an agent's memory:

**1. The provenance ledger** (`pf.provenance`, `docs/GOVERNANCE.md`). Every
action lands as five stages: intent (before), decision (the gate), execution
(after), a SHA-256 chain linking them, and an RFC 3161 + OpenTimestamps anchor
over the head. Hooks write stages for tool calls, `pf.agents.base` for LLM
calls, `pf.provenance.action()` for everything else — warehouse custody
included. `provenance/**` is denied to every agent: you may not edit the
record of what you did. `pf provenance verify` is the audit and blocks CI.

**2. The path gate** (`gate.yaml` + generated `gate.capabilities.yaml`).
Enforced by the PreToolUse hook, the pre-commit hook and `pf gate`: a denylist
(secrets, the ledger, generated artefacts, the warehouse files, the quack
state file), a `platform_denylist` that stops a project session from touching
shared infra, `impact_required` paths, a per-loop file cap, and a
`blockOn: breaking` severity line.

**3. Named controls** (`policy.yaml` + `pf air`, `docs/AIR.md`). Every policy
entry carries `enforced_by` pointing at a real artefact — a symbol, a config
section, a path — and `controls:` ids from the vendored FINOS AI Governance
Framework, which cross-walks to the EU AI Act, ISO 42001, NIST and OWASP.
`pf air coverage` *derives* whether each named enforcement actually resolves
(never stores it), and `pf air gate <g> <p>` blocks the merge on the controls
that entity committed to in its `air.yaml`. A control whose enforcement
resolves to nothing reports as failing — which is the point.

**4. Impact analysis as the merge gate** (`pf impact`, `pf pr report`).
The graph names every downstream model, metric, dimension and exposure — with
owners — before a change lands; recce supplies the empirical half on real
data. Three enforcement points: `pf check` (CI/on demand), the pre-commit hook
(blocks breaking, `--no-verify` requires a reason), and the PreToolUse hook
(prints blast radius before an edit). Loop-engineering (`LOOP.md`,
`loop-constraints.md`, budgets, circuit breaker) bounds what an autonomous
loop may do at all.

## The session layer

How an agent actually works here (`docs/CLAUDE-CODE.md` is the runbook):

- **Scoped sessions.** `uv run pf work <g> <p>` launches Claude with cwd
  inside exactly one project; the path gate makes the scope binding, and the
  root `CLAUDE.md` router plus the project's context card keep the preamble
  near 1000 tokens.
- **The `power-tools` toolkit** ships the `pf` MCP server (`kg_search`,
  `kg_neighbors`, `kg_path`, `impact_analysis`, `dbt_*`, metrics and secrets
  tools), read-only verification subagents (impact-verifier, secrets-auditor,
  semantic-conformance, sql-reviewer), and the format/notify hooks. Ask the
  graph before reading files; run `impact_analysis` before changing a column,
  a model or a metric.
- **The control plane** (`docs/STACK.md`): OpenMetadata, Dagster and recce on
  one origin behind nginx in one container (`pf_stack`), one Postgres split by
  schema, recce state in the artefact store (`docs/ARTIFACTS.md`). `pf ui`
  (:8787) is the lightweight dashboard reading the same JSON CI writes.

## Extension seams

Where the platform grows, and deliberately nowhere else:

1. **`pf.scaffold.bootstrap.STEPS`** — one ordered, idempotent list of
   post-scaffold work. `pf new-project` runs it for new projects;
   `pf bootstrap --all` retrofits every existing one. Adding a platform
   capability means adding a step here, and old and new projects converge.
   (`pf bootstrap-steps` prints what runs and why each step exists.)
2. **The Tool framework** — a `Tool` declaration (a `pf.tools` entry point in
   any installed package) yields scaffolded files, gate rules, Dagster assets
   and a UI panel without editing the scaffolder, the CLI or the UI. Enabled
   in `tools.yaml` at group (inherited by every sister) or project level.
   `pf.tools.recce` is the reference implementation.
3. **Capabilities** contribute gate rules (`gate.capabilities.yaml`) and CI
   jobs — `.github/workflows/*` are *generated* per project from declared
   `ci_jobs`; hand-editing one is overwritten by the next bootstrap.
4. **Toolkits** — new agent skills land as plugins under `platform/toolkits/`
   and register in `ROUTING.md`.
5. **Vendoring** — new upstreams enter as pinned submodules with a
   `registry.yaml` entry recording exactly what was adopted.

## Invariants

The rules that hold everywhere, restated once:

- `platform/**` is never edited from a project session; `vendor/**` is never
  edited from any session. Pin bumps are human decisions.
- Never read another group or another sister project.
- `provenance/**` is written only by the runtime; the ledger is
  tamper-*evident* by hash chain and tamper-*denied* by gate.
- Generated artefacts (staging, projections, workflows, cards, graphs) are
  changed by changing their source declaration, never by hand.
- Secrets never enter git: the gate denies the paths, tokens print redacted,
  the state files are 0600.
- Every write to a dev warehouse goes through a write window; every read goes
  over the read-only wire, on ADBC/Arrow.
- A control without a resolving `enforced_by` is a failing control, not a
  documented one.

## Document index

| Doc | Covers |
|---|---|
| `README.md` | the front door: quick start, daily commands, token budgets |
| `CLAUDE.md` (root) | the session router: layout, gates, where to work |
| `docs/STACK.md` | the control plane: OpenMetadata + Dagster + recce, one origin |
| `docs/GOVERNANCE.md` | the provenance ledger: stages, chain, anchoring, verification |
| `docs/AIR.md` | named controls: FINOS crosswalk, coverage, the per-entity gate |
| `docs/ARTIFACTS.md` | the artefact store: what leaves git and how it travels |
| `docs/SEMANTICS.md` | the semantic layer and its projections |
| `docs/VENDOR.md` / `docs/VENDOR-CARD.md` | every upstream, every borrowing, every contract |
| `docs/CLAUDE-CODE.md` | the session layer: MCP tools, subagents, hooks |
| `docs/COMMITTER.md` | commit segregation by a local model (`pf commit`) |
| `groups/<g>/projects/<p>/docs/quack.md` | per-project dev-serving runbook (generated) |
