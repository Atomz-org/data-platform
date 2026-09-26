# Project in a group, the regeneration order, and delivery

What `SKILL.md` Phases 0, 2 and 13 rely on. Every command here exists in `pf`
and is checked by `test_requirement_pipeline_skill.py`; every order here is one
the gate or CI enforces. Worked example throughout: a multi-entity exchange
feed added to a project of a commodity group (one pipeline and one job per
traded commodity, two new group-tier classes, 270 files in 29 commits).

## 1. Where the build lands

| Tier | Path | Changed by this skill | How |
|---|---|---|---|
| platform | `platform/**` | never | handed back (`skill-map.md` §Out of scope) |
| group | `groups/<g>/` — `ontology/extension.yaml`, `shared/python`, `shared/transform`, `okf/`, `tools.yaml`, `group.yaml` | only through a planned `group_changes` entry | `design-ontology`, the group's own skills |
| sister | `groups/<g>/projects/<other>/` | only their generated files (OKF bundles, maps) | `pf tool okf build --all`, `pf harness <g>` — never by hand, never read |
| project | `groups/<g>/projects/<p>/` | yes | every phase |

The group's own skills (`groups/<g>/.claude/skills/`) encode the family's
conventions — how an entity is added, how prices are compared, how a feed is
triaged. The validator lists them; read them in Phase 0 and prefer them to a
generic route where they overlap.

## 2. A new project

1. `uv run pf new-group <g>` only when the spec sets `target.new_group` (a new
   family is a decision, not a side effect).
2. `uv run pf new-project <g> <p> --plan` — writes nothing; ★ confirm.
3. `uv run pf new-project <g> <p>` — scaffolds the project (`src/<pkg>/`,
   `transform/`, `.dlt/`, `decisions/`, `.memory/`, `kg/`, `tools.yaml`), applies
   the default capabilities, merges its gate rules, and runs the bootstrap
   ladder (graph and card, MDL, otop, settings, inherited tools, the CI
   workflow `.github/workflows/<p>.yml`, the Dagster location, `kg/architecture.md`,
   the three harness maps). Exit: `uv run pf check` shows 0 errors (a missing
   `contracts/annotations.yaml` warning is expected).
4. Registration that is **not** automatic: the group's entity seed, the
   `group.yaml` resources, the roll-up roster — through the group's own skill.
   The uv workspace is a glob (no edit), but `uv.lock` changes and is committed;
   `platform/workspace.yaml` is machine-local and never committed.
5. Continue at Phase 1 with the requirement as the project's first content.

## 3. A group-tier change

When the word, the connector or the rule is not the entity's own — a futures
contract is the same thing on every exchange, so its class goes in the group
ontology, not the project's:

1. `group_changes` entry with its `why` (the validator refuses one without).
2. Edit `groups/<g>/ontology/extension.yaml` (classes, properties with roles,
   relations) and any group test it affects.
3. A source only this entity has, in a group whose conformance test holds
   `models/staging` (or `models/intermediate`) identical across sisters, needs a
   `conformance_exemption`: the test exempts that source's directories and
   nothing else, and a new test proves the exemption is that narrow.
4. `uv run pytest groups/<g>/shared/python/tests` — no workflow runs the group's
   tests; this is the only check.
5. `uv run pf tool okf build <g> <p> --group`, then `uv run pf tool okf build --all`
   (every sister's bundle re-emits the shared concepts), then `uv run pf harness <g>`.
6. `uv run pf tool okf check --all` and `uv run pf harness check`.

## 4. The regeneration order

Each step reads what the one before it wrote. Out of order, the output is
confidently stale.

| # | Command | Writes | Needs first |
|---|---|---|---|
| 1 | `pf gen-staging <g> <p>` (`--overwrite` after an annotation change) | staging models and sources yml | `contracts/annotations.yaml` |
| 2 | `pf seed <g> <p>` | warehouse (runs `src/<pkg>/seed.py`), then graph and card | the source registered in `seed.py` |
| 3 | `pf kg build <g> <p>` | `kg/graph.json` | a default-target manifest (re-parse after a recce baseline) |
| 4 | `pf semantic mdl <g> <p>` | `mdl/mdl.json`, and the Wren workspace's tracked half (`mdl/wren/wren_project.yml`, `mdl/wren/knowledge/rules/`) | 3 |
| 5 | `pf report build <g> <p>` | metric pages, `pages/index.md`, sources, exposures | 4, and a seeded warehouse |
| 6 | `pf kg build`, `pf semantic mdl` again | graph and MDL with the new exposures | 5 |
| 7 | `pf tool openmetadata payload <g> <p>` | `catalog/openmetadata.json` | 6 |
| 8 | `pf tool okf build <g> <p> --group` | `okf/**` | 6 |
| 9 | `git add` the content, then `pf arch <g> <p>` | `kg/architecture.md` | the git index (untracked files do not count) |
| 10 | per commit: `pf harness <g> <p>` | the three harness maps | the git index |
| 11 | `pf memory add groups/<g>/projects/<p> <slug> "<line>"` | `.memory/notes/`, `.memory/MEMORY.md` | — |
| 12 | only if `platform/` changed: `pf context refresh` | test index, architecture, onboarding | — |

`pf context refresh` heals the repository-level files, MDL, OKF and maps; it
does not rebuild `kg/graph.json` or `kg/architecture.md` (steps 3 and 9 do).

## 5. Delivery: commits the gate accepts

The pre-commit gate judges every commit; the pre-push hook and CI judge them
again (`pf gate --commits origin/main..HEAD`).

- **At most 12 files per commit** (`maxFiles`), maps included. A commit that
  truly cannot be split carries a `Gate-Exempt: <reason>` trailer; a build never
  needs one.
- **Harness maps travel with the change that moves them** (`harness_required`).
  They render from the git index, so per slice: `git add <slice>` →
  `pf harness <g> <p>` (`pf harness <g>` for a group slice) → `git add` the maps
  that changed → commit. A group slice moves the group, project and reporting
  maps together.
- **Pipeline order**: platform prerequisites (handed back) → group tier →
  sister bundles → requirement record and ingestion (with its tests, seed,
  `uv.lock`, ADR) → staging → intermediate → marts and tests → semantic layer
  and exposures → orchestration and runbook → hand-written pages → report
  sources → generated metric pages → OKF → graph, MDL and catalogue → memory
  index. `scripts/plan_commits.py` produces exactly this from
  `git status --porcelain -uall`, leaving room in each slice for its maps and
  refusing paths that never ship.
- **Never shipped**: `vendor/`, `provenance/`, `*.duckdb`, `platform/workspace.yaml`,
  secrets, `kg/graph.duckdb`, `kg/context_card.md`, build output.
- An accepted ADR changes only its Status line; a correction is a new ADR.
- A refusal is final: report it. Never `--no-verify`, never reroute around it.
- `/ship` is user-invoked. The agent plans the slices; the user commits.

## 6. CI checklist (run before asking for review)

| Check | Command | Guards |
|---|---|---|
| lint | `uv run ruff check platform/` | toolkit scripts are linted too |
| platform tests | `uv run pytest platform/tests -q` | skill routing, toolkit registration, test index |
| group tests | `uv run pytest groups/<g>/shared/python/tests` | conformed paths (no workflow runs these) |
| project tests | `uv run pytest groups/<g>/projects/<p>/tests` | connectors (no workflow runs these) |
| gates | `uv run pf check`, `uv run pf tokens`, `uv run pf group verify` | ontology conformance, token budgets |
| per project | `uv run pf kg build <g> <p>` then `uv run pf arch <g> <p> --check`; `uv run pf air gate <g> <p>` | the map, committed controls |
| generated context | `uv run pf context check`, `pf memory check`, `pf test check`, `pf arch check`, `pf guide check`, `pf harness check` | stale generated files |
| semantic and OKF | `uv run pf semantic mdl --check --all`, `uv run pf tool okf check --all`, `uv run pf tool wren check --all` | MDL, bundles and Wren workspaces current |
| commits | `uv run pf gate --commits origin/main..HEAD` | 12-file cap per commit |
| PR report | `uv run pf pr report --base origin/main` | verdict `review`, never `block` |

The per-project workflow runs only when that project's paths change; the
platform workflows run on `platform/**`; agent context runs on every PR.
