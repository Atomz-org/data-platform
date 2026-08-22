# Scaffolding a project

Three commands. The middle one is the point.

```bash
uv run pf new-group   <group>                    # only if the group is new
uv run pf new-project <group> <project> --plan   # decide
uv run pf new-project <group> <project>          # apply
```

Code: [`platform/src/pf/scaffold/`](../platform/src/pf/scaffold/) — `plan.py`
(the decision), `generator.py` (the files), `bootstrap.py` (everything after).
Skill: `platform-init/scaffold-project`.

---

## Why plan first

Scaffolding is cheap to run and expensive to run **wrong**. `pf bootstrap`
backfills what a project is missing, but it never removes what should not have
been added — a capability enabled by mistake is corrected by hand, in a project
somebody has to notice first.

`--plan` resolves the whole scaffold and writes nothing:

```console
$ uv run pf new-project demo demo-us --plan
plan: demo/demo-us
  path       groups/demo/projects/demo-us
  enabling   3 capability(ies)
    evidence       2 file(s)
    github         1 file(s) · ci: impact-gate
    snowflake      2 file(s) · env: SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_DATABASE
  gate       +6 rule(s): denylist ×5, impact_required ×1
  ci         impact-gate
  [!]        capability 'snowflake' needs unset env: SNOWFLAKE_ACCOUNT, …

  apply with the same command minus --plan
```

It exits **0** when clean and **1** when blocked, so it works in a script as
well as in a session.

### The token argument

This is the part that matters for an agent, and it is measured rather than
asserted:

| Question | Old way | Cost | Now |
|---|---|--:|--:|
| which capabilities exist, what do they add | `pf capabilities` | ~960 | in the plan |
| what does this one contribute | read `pf/capabilities.py` | ~7,000 | in the plan |
| does the group exist | `ls groups/` | ~50 | in the plan |
| is the directory taken | `ls groups/<g>/projects/` | ~50 | in the plan |
| **total** | | **~8,000** | **~124** |

The plan is one call and about thirteen lines. It replaces exploration whose
answers are short, fixed, and knowable by the scaffolder — which is the whole
category of thing that should never cost an agent a file read.

The apply path pays the same attention: its output dropped from ~491 tokens to
~459 *while gaining* a `next` block, by printing a count of the gate rules it
merged instead of the six glob patterns, which are identical every time and
already in `gate.capabilities.yaml`.

---

## Blockers, and why these two

A plan that lists what *would* happen but not what would *stop* it is a plan you
still have to try before you trust. Two things stop a scaffold, and both are
mistakes that have actually been made:

**The group does not exist.** A project lives at
`groups/<group>/projects/<project>`, so scaffolding a sister into a group nobody
created yet fails partway, leaving a directory that is not a project.

**The directory is already taken.** The generator would write over a live
project. The plan reports how many files are there, and names the two things you
probably meant instead:

```
BLOCKED    groups/acme/projects/acme-us already exists (47 file(s)). To add a
           capability to it use `pf capability-add`; to bring it up to the
           current platform use `pf bootstrap acme acme-us`
```

Apply refuses on the same conditions — `--plan` is a convenience, not the only
guard.

### Warnings are not blockers

A missing credential warns and proceeds. A production target is **inert** until
`DBT_TARGET=prod` asks for it, and every project is created on a machine that
cannot reach its warehouse. Blocking there would block the normal case.

A roll-up over a group with no sisters warns too: it will union nothing until
one exists, which is fine when the roll-up is created first on purpose.

---

## Group or project?

A **group** is a family of sister companies sharing an ontology instance,
conformed dimensions and group metrics. A **project** is one legal entity with
its own warehouse and its own dlt and dbt.

Put a new entity in an existing group only if a roll-up across it and its
sisters would be arithmetically meaningful. Two companies that mean different
things by `Payment` cannot be summed, and the roll-up is where that surfaces —
as a number, silently. If the vocabulary does not transfer, it is a new group.
That costs one `pf new-group`.

---

## Choosing capabilities

The defaults are right for most projects. Change them for a stated reason:

| Situation | Flag |
|---|---|
| production is BigQuery / Redshift / ClickHouse | `--with bigquery --without snowflake` |
| no BI layer | `--without evidence` |
| not on GitHub | `--without github` |
| cross-entity roll-up | `--rollup --sisters a,b` |

`uv run pf capabilities` lists everything. `--plan` tells you what the ones you
picked will actually do, which is the question you have while deciding.

---

## What apply does

`pf new-project` is not just a file writer. Everything after the files lives in
`pf.scaffold.bootstrap.STEPS`, shared with `pf bootstrap`, and runs here too:

knowledge graph · context card · group card · MDL · OWL · otop manifest · vendor
docs · reporting · enabled tools · capabilities · CI workflow · Dagster code
location · dbt wiring · conformance check

That sharing is deliberate and was learned the hard way: the steps used to be
inlined in `new-project`, so every capability added later had to be hand-patched
into existing projects, and each one was a silent hole until somebody noticed.

It is **idempotent**. If a step reports `✗`, re-run `uv run pf bootstrap <g>
<p>` — never hand-edit the output.

---

## Verifying, and stopping

```console
✓ project demo/demo-us created with 22 files
  ✓ knowledge graph          99 nodes across 6 kinds
  ✓ context card             ~106 tokens / 1500
  …
  next
    1. pf seed demo demo-us  load data, build dbt, refresh the graph
    2. /quick-start          source → annotations → mart → metric
    3. pf check              conformance, before the first commit
  what you got: groups/demo/projects/demo-us/kg/context_card.md — read that,
  not the scaffolded files
```

Three exit criteria: the command exits 0, no line starts with `✗`, and
`pf check` reports 0 errors. A warning about a missing
`contracts/annotations.yaml` is expected — nothing has been ingested yet.

That last line is the habit worth keeping. The scaffolder knows what it made;
reading twenty-two generated files to rediscover it is the most expensive
possible way to learn something you were just told. The card is the index, and
it is regenerated by `pf kg card` rather than maintained.

---

## Failure modes

| Output | Fix |
|---|---|
| `group '<g>' does not exist` | `pf new-group <g>` |
| `already exists (N file(s))` | `pf bootstrap` to update, `pf capability-add` to add one thing |
| `✗` on a bootstrap step | re-run `pf bootstrap <g> <p>`; steps are independent |
| `needs unset env` | expected without credentials; proceed or `--without` |
| a `UserWarning` about `sqlglot[rs]` | should no longer appear — see below |

### The sqlglot warning

It used to print in the middle of every scaffold. It is filtered in
`pf/__init__.py`, narrowly, by message rather than by category, and the reason
is that its advice is wrong here: `pyproject.toml` pins `sqlglot` specifically
to keep `sqlglotc` out, because Wren subclasses sqlglot's Parser in pure Python
and an interpreted class cannot inherit from a compiled one. Following the
warning breaks every MDL query that resolves a model.

---

## Adding to the scaffold

Do not edit the generator. A capability declares what it contributes — files,
settings, gate rules, CI jobs — and one entry in `pf.capabilities.CAPABILITIES`
reaches every project, new and existing, through `pf bootstrap --all`. A `Tool`
does the same for something that also runs.

A new capability appears in `--plan` automatically, because the plan is
generated from the registry rather than describing it.
