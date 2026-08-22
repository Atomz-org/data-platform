---
name: scaffold-project
description: Create a new group or project in this platform. Use when the user says "add a company", "new project", "onboard an entity", or names a business unit that has no directory yet. Not for importing an existing dbt repo — that is onboard-project.
---
# Scaffold a project

Three commands, in this order. Everything else here exists to keep you from
reading files to work out what they did.

```bash
uv run pf new-group   <group>                    # only if the group is new
uv run pf new-project <group> <project> --plan   # decide
uv run pf new-project <group> <project>          # apply
```

**Run `--plan` first, always.** It resolves the whole scaffold and writes
nothing, in ~120 tokens. That is cheaper than one `pf capabilities` call (~960)
and far cheaper than reading the registry, and it is the only thing that catches
the two failures that actually happen: the group does not exist yet, or the
project directory is already taken.

Never `mkdir` a project by hand. A half-scaffolded project has no gate hook, no
graph and no CI, and nothing reports that — it simply is not governed.

## group or project?

A **group** is a family of sister companies sharing an ontology instance,
conformed dimensions and group metrics. A **project** is one legal entity with
its own warehouse.

Put a new entity in an existing group only if a roll-up across it and its
sisters would be arithmetically meaningful. If `Payment` would mean something
different, it is a new group — that costs one `pf new-group` and keeps the
roll-up honest.

## choosing capabilities

The defaults are already right for most projects. Change them only for a stated
reason:

| Situation | Flag |
|---|---|
| production is BigQuery / Redshift / ClickHouse | `--with bigquery --without snowflake` (default is `snowflake`) |
| no BI layer wanted | `--without evidence` |
| the project is not on GitHub | `--without github` |
| cross-entity roll-up over sisters | `--rollup --sisters a,b` |

Do **not** read `platform/src/pf/capabilities.py` to decide. `--plan` prints
what each enabled capability contributes; `uv run pf capabilities` lists every
one if the user asks what is available.

A missing credential is a warning, not a blocker — a production target is inert
until `DBT_TARGET=prod` asks for it. Scaffold anyway.

## verify, then stop

`pf new-project` runs the whole bootstrap itself: graph, cards, MDL, OWL, otop,
gate rules, CI workflow, Dagster location. It is idempotent, so if anything
looks wrong the fix is `uv run pf bootstrap <group> <project>`, never a hand
edit.

Exit criteria, in order:

1. The command exits 0 and prints `✓ project <g>/<p> created`.
2. No line in its output starts with `✗`.
3. `uv run pf check` reports 0 errors. One warning about a missing
   `contracts/annotations.yaml` is expected — nothing has been ingested yet.

Then **stop and show the user the `next` block**. Do not start ingesting in the
same turn; picking the source is their decision, and the scaffold is a natural
checkpoint.

## do not read these

The scaffolder already said what it made. Reading the tree to find out costs
thousands of tokens and teaches you nothing the output did not.

- the scaffolded project files — `kg/context_card.md` is the index, and it is
  regenerated rather than hand-maintained
- `platform/src/pf/capabilities.py`, `scaffold/generator.py`, `scaffold/ci.py`
- `gate.capabilities.yaml` — generated, and `--plan` already counted the rules

## when it fails

| Output | Fix |
|---|---|
| `group '<g>' does not exist` | `uv run pf new-group <g>` |
| `<path> already exists (N file(s))` | already scaffolded — `pf bootstrap <g> <p>` to update it, `pf capability-add` to add one thing |
| `✗` on a bootstrap step | re-run `pf bootstrap <g> <p>`; steps are independent and idempotent |
| `needs unset env` | expected without credentials — proceed, or `--without <capability>` |
| `no such command` | you are outside the repo, or `uv sync` has not run |

## after scaffolding

`/quick-start` takes it from an empty project to a queryable metric. Do not
start it unprompted.
