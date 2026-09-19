# The per-project architecture map

Every project carries a generated map of itself at `kg/architecture.md`. It
answers, in about 2,000 tokens, the questions an agent or a new engineer would
otherwise answer by reading twenty directories:

- how data moves through *this* project, with its real counts on every stage
- which actual model feeds which actual metric — named, not generic
- what would stop a bad change, and what each control reads to decide
- **every feature it has, and every feature it does not**

```bash
uv run pf arch <group> <project>            # write it, and print the gaps
uv run pf arch <group> <project> --show     # print it, write nothing
uv run pf arch --all --check                # CI: stale map, or an unmapped feature
uv run pf arch <group> <project> --json     # machine-readable summary
```

You rarely run any of these. `pf new-project` and `pf bootstrap` both write the
map, so a scaffolded or bootstrapped project already has a current one.

Code: [`platform/src/pf/architecture.py`](../platform/src/pf/architecture.py)
(the designer), [`platform/src/pf/viz.py`](../platform/src/pf/viz.py) (the
palette and the linter). Skill: `platform-init/design-architecture`.

---

## Why it is a registry, not a template

The obvious way to build this is a template with the sections someone thought of
on the day. That is precisely how a project feature goes missing: `catalog/` and
`evals/` were both added to the scaffolder long after the first overview of a
project was written, and neither appeared in any of them until somebody noticed.

So the document is generated from `pf.architecture.FEATURES` — one entry per
thing a project can have — and two properties follow that a template cannot give
you:

**Every feature is reported, including the absent ones.** A project with no
exposures is a project whose impact analysis stops at its marts. That is
invisible in a directory listing, and it is a row in this table.

**Everything else is flagged.** Any top-level entry in the project that no
feature claims is listed under *Unmapped*, and `pf arch --check` fails on it. A
directory added by a future capability shows up as a hole in the map rather than
not showing up at all.

That second one is not theoretical. On its first run against a freshly
scaffolded project it reported `tools.yaml` as unmapped — a per-project tool
override file that the scaffolder writes, that none of the eight existing
projects had, and that nothing had ever documented.

### Adding a feature

One entry. It reaches every project, new and existing, on the next
`pf bootstrap --all`; there is no per-project step and nothing to retrofit.

```python
Feature("catalog", "catalog export", "semantics",
        "OpenMetadata ingestion, for a company that runs one",
        ("catalog/openmetadata.json", "catalog/ingestion/**"),
        optional=True, made_by="pf bootstrap"),
```

| Field | When it matters |
|---|---|
| `optional=True` | absence is a decision, not a gap — a capability nobody enabled |
| `count_kind` | a graph count is truer than a file count: one YAML declares six metrics |
| `repo_paths` | the artefact is *about* the project but lives outside it (CI, Dagster) |
| `made_by` | printed beside every absent row, so a gap is actionable |

Detection is by path glob rather than by asking a subsystem, deliberately: a
feature has to be detectable in a project that cannot import its own code, has
no warehouse and has never been built. That is every project at scaffold time,
and every project on a CI runner without credentials.

---

## Scope: one project, never a sister

Nothing in the designer reads outside the project directory, with two
exceptions, both of which are artefacts *about* this project rather than about
another entity: its CI workflow and its Dagster code location. A roll-up
additionally lists its sisters' **names**, from the same directory listing the
group card already publishes — no sister file is opened.

`test_gathering_reads_nothing_outside_its_own_project` enforces this by spying
on `Path.read_text` and failing on any read under another group or another
project.

---

## Why it is committed, and why it has no date

`kg/context_card.md` is generated and *not* committed. This file is generated
and **is**. The difference is one line: the card stamps its generation date, so
committing it would rewrite eight files every day and say nothing.

The map has no date by design. It changes when the project changes, which makes
three things work:

- a pull request that adds an exposure shows what that did to the shape of the
  project, in the diff, next to the change
- `pf arch --check` measures drift rather than noise
- `pf bootstrap --all` is a no-op diff on a repository nobody has touched

**What `--check` needs.** Every number on the map comes from the annotations and
the dbt manifest, both of which travel with the checkout — so the same commit
produces the same map on any machine, *once the graph is built*. Run
`pf kg build` first in CI, as the impact-gate job already does; without a
manifest the graph holds no models and the check reports drift that is really a
missing build. This is also why the control diagram names the graph rather than
counting it: columns are backfilled from `information_schema`, so a total node
count differs between a laptop with a warehouse and a runner without one.

It is on the gate's `denylist` (an agent may not hand-edit it) and its
`denylist_except` (git may carry it) — the same pair as `mdl/mdl.json` and the
generated CI workflows.

---

## The diagrams

Three, and no more: a diagram with sixty boxes is read by nobody.

| Diagram | What only it can show |
|---|---|
| The spine | the shape of the pipeline, and which stages are empty |
| A real path through it | that `revenue` is actually built from `stg_stripe__charges` |
| What enforces what | the control path, which runs *across* the pipeline rather than along it |

They follow `viz-standards/charts-and-diagrams`, and the palette lives in
`pf.viz` rather than in any renderer — `pf.pr` draws the same layers on a pull
request and must use the same hues. Pale fill, saturated stroke of the same hue,
near-black ink: GitHub renders one source on both a light and a dark page and
does not recolour an explicit `classDef`, so a fill chosen against white is
unreadable on black and no media query can save it.

A node with a count of zero is drawn grey and labelled *none yet* rather than
omitted. The shape of the map is then identical in every project — a reader who
knows one knows them all — and a hole is visible as a hole.

`viz.lint` checks each generated block for the four defects that are invisible
in the source and expensive in the render: an edge to an undeclared node, two
nodes sharing an id (mermaid merges them and a layer vanishes), a class used but
never defined, and a raw `<` in a label (swallowed as a tag). A malformed
diagram renders as a red box while the job that produced it exits 0, which is
why this is a test and not an eyeball.

---

## Budget

4,000 tokens, checked by the bootstrap step. Every section is capped, because
jaffle-shop has 996 marts and the map that grows with the project is the one
that silently stops being cheaper than reading.

Measured across the eight projects: 2,000–2,200 tokens. When one goes over, cap
a section — do not raise the budget.

This is the **on-demand** tier, not the always-on one. It is read when an agent
needs the map, not loaded into every session; the always-on index is the context
card at ~400 tokens.

---

## Failure modes

| Output | What it means |
|---|---|
| `map is stale` | the project changed after the map was written — `pf arch <g> <p>` |
| `no architecture map` | never bootstrapped — `pf bootstrap <g> <p>` |
| `N unmapped entry(ies)` | the registry is behind the platform — add a `Feature` |
| `diagram N: …` | a mermaid defect in generated output; fix the renderer, not the file |
| over budget | cap a section |

Never hand-edit the file. The next bootstrap overwrites it, and `pf arch
--check` fails on the drift in the meantime.
