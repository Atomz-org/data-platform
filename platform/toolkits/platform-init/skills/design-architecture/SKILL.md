---
name: design-architecture
description: Understand or document how one project is built — its pipeline, its features and what is missing. Use when the user asks "how does this project work", "what's the architecture", "what are we missing", or when you would otherwise start reading a project's tree to orient yourself. Also for adding a new project feature to the map.
---
# Design a project's architecture

Every project has a generated map at `kg/architecture.md`. **Read it before you
read anything else.** It is ~2,000 tokens and replaces the twenty-file walk that
would otherwise be your first act in an unfamiliar project.

```bash
uv run pf arch <group> <project>            # write it (and print gaps)
uv run pf arch <group> <project> --show     # print it, write nothing
uv run pf arch --all --check                # stale map, or an unmapped feature
uv run pf arch <group> <project> --json     # machine-readable summary
```

You rarely need to run any of these. `pf new-project` and `pf bootstrap` both
write the map, so a project that has been scaffolded or bootstrapped already has
a current one. Run `pf arch` when you have just changed the project's shape and
want the map to catch up before committing.

## what it tells you, that a file walk does not

| Section | The question it answers |
|---|---|
| The spine | how data moves here, with this project's real counts on every stage |
| A real path through it | which actual model feeds which actual metric — named, not generic |
| What enforces what | which control would stop a bad change, and what it reads to decide |
| Every feature, present or not | the whole inventory, **including the absent rows** |
| Gaps | what is missing, and the exact command that fixes each one |

The fourth section is the one to trust. It is generated from
`pf.architecture.FEATURES`, not from a template, so a feature cannot be quietly
left out of it — and absent features are listed rather than omitted. A project
with no exposures is a project whose impact analysis stops at its marts, and
that is invisible in a directory listing and obvious in this table.

## reading it, not the tree

Orienting in a project is a routing problem, and the tools for it are in this
order:

1. `kg/context_card.md` — always loaded; what data exists
2. `kg/architecture.md` — this map; how the project is built and what is missing
3. `kg_search` / `kg_neighbors` / `kg_path` / `impact_analysis` — the specifics
4. the files — only once you know which one

Going straight to step 4 costs thousands of tokens to rediscover what steps 1–3
would have told you, and it is how an agent ends up reading a sister project by
accident. **Never read another group or another sister project**, whatever the
map appears to invite; the roll-up is the only place cross-entity questions are
answered.

## adding a feature to the map

If you have added something to a project that the map does not mention, the fix
is one entry in `pf.architecture.FEATURES` — never a hand edit of the document,
which the next bootstrap overwrites.

```python
Feature("catalog", "catalog export", "semantics",
        "OpenMetadata ingestion, for a company that runs one",
        ("catalog/openmetadata.json", "catalog/ingestion/**"),
        optional=True, made_by="pf bootstrap"),
```

Set `optional=True` when absence is a decision rather than a gap — a capability
nobody enabled. Set `count_kind` when a graph node count is truer than a file
count: one YAML file can declare six metrics, and "1 file" is the wrong answer.

The registry reaches every project at once, new and existing, because
`pf bootstrap --all` regenerates every map. There is no per-project step and
nothing to retrofit.

**`pf arch --check` fails on an unmapped directory.** If a project holds a
top-level entry no feature claims, that is a hole in the registry and CI says
so. Do not silence it by adding the name to `IGNORED` — that list is for build
output and editor droppings, not for features nobody has documented yet.

## when you are drawing, not reading

The diagrams follow `viz-standards/charts-and-diagrams`, and the palette lives
in `pf.viz` rather than in any one renderer. If you add or change a diagram:

- take colours from `viz.PALETTE` and emit them with `viz.classdefs` — never
  hard-code a fill, and never introduce a hue that is not already in the palette
- put every interpolated string through `viz.esc` — an unescaped `#` or `"` is a
  parse error that renders as a red box while the job still exits 0, and a raw
  `<` is silently swallowed as a tag
- generate synthetic node ids (`T1`, `X0`). Two boxes sharing an id do not
  error; mermaid merges them and a layer vanishes
- run `viz.lint` on the result — it catches all three of the above

## when it fails

| Output | What it means |
|---|---|
| `map is stale` | the project changed after the map was written — `pf arch <g> <p>` |
| `no architecture map` | never bootstrapped — `pf bootstrap <g> <p>` |
| `N unmapped entry(ies)` | the registry is behind the platform — add a `Feature` |
| `diagram N: …` | a mermaid defect in the generated output; fix the renderer |
| `~N tokens / 4000` over budget | the map is growing with the project — cap a section, do not raise the budget |
