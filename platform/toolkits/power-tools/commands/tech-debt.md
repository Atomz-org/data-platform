---
name: tech-debt
description: Inventory the active project's debt — ungoverned models, unannotated sources, stale decisions, inert gates — and rank it by what it actually costs.
disable-model-invocation: "yes"
---

# Tech debt

Debt in a data platform is mostly **governance that went inert**: a gate that
cannot fire, a graph that no longer matches the models, a contract nobody
regenerated. Those are cheap to find and expensive to leave.

Scope: `$ARGUMENTS` (`governance`, `models`, `docs`, `tools`), else all.

## 1. Inert governance — check first, it is the costliest kind

```bash
uv run pf loop audit                # scored: gate, hooks, graph, cards, ledger
uv run pf tool doctor <group> <project>
uv run pf tokens                    # always-on context budget
```

Each of these is a specific class of debt:
- **no `kg/graph.duckdb`** → the PreToolUse gate warns instead of reporting a
  blast radius. The project is ungoverned; edits land unverified. `pf kg build`.
- **stale graph** → worse than none, because it reports a blast radius that is
  wrong. Compare graph mtime against the newest file under `transform/models/`.
- **`pf tool doctor` gaps** → a tool is enabled in `tools.yaml` but its package
  is not installed, so its gate rules exist and never run.
- **card over budget** → every session pays it, forever.

## 2. Model debt

```bash
uv run dbt ls --select "resource_type:model" | wc -l
```

Then, via the graph:
- models absent from the graph (built after the last `pf kg build`),
- models nothing consumes — dead, but still built and tested every run,
- models with no test and no contract, especially any that a metric depends on,
- `select *` in staging, which makes every upstream schema change a silent one,
- duplicated logic across models that should be one intermediate.

## 3. Source debt

Resources without `@annotate`; annotations whose concept no longer exists in the
ontology; `links` pointing at a class the topology does not relate. Each one is a
join that will be guessed later.

## 4. Documentation and decisions

- `decisions/ADR-*.md` that describe a state no longer true — an ADR that lies is
  worse than a missing one.
- `CLAUDE.md` "Business rules the graph cannot encode" still empty on a project
  that plainly has some.
- `evals/cases/` that no longer match the models they assert on.

## 5. Rank and report

One table. For each item: **cost now** (what it makes slow, risky or wrong),
**cost of the fix**, **trigger** (what event makes it urgent — a new sister, a
schema change, an audit). Then three buckets:

- **Fix now** — anything that makes a gate inert. It is silently disabling a
  control, which is the only kind of debt that gets worse without being touched.
- **Fix next** — real cost, bounded work.
- **Accept** — with the reason written down, so it is a decision and not an
  oversight. Put these in an ADR.

Do not open the fixes as part of this command. Inventory first.

---

## Generic checklist (retained from the source guide)

**Code** — duplicated logic, dead code, TODO/FIXME/HACK markers, missing error
handling, weak typing (`any`/`unknown` without a reason), inconsistent patterns.
**Dependencies** — outdated or unmaintained packages, known vulnerabilities,
dependencies added without discussion, heavy libraries where a small one works.
**Tests** — coverage gaps on critical paths, flaky tests, tests asserting
implementation rather than behaviour.
**Docs** — stale README, undocumented public functions, missing ADRs.

**Output format** — a prioritised assessment: what to fix now, what to schedule,
what to accept and why.
