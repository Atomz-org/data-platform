---
name: blast-radius
description: Report what breaks if a model, column or metric changes. Run this before editing anything in the graph, not after.
---

# Blast radius

Target: `$ARGUMENTS` — a node (`model:stg_orders`, `column:orders.status`,
`metric:revenue`), or nothing, in which case use what you have already changed.

## Fastest path

```bash
uv run pf impact <group> <project> <node>
```

or, in a session where the `pf` MCP server is up, `impact_analysis("<node>")` —
same answer, no shell round-trip.

For everything currently modified, without naming nodes:

```bash
uv run pf check          # ontology conformance + blast radius of your changes
```

## Reading the result

The report is downstream reach, not a verdict. Judge it:

- **models** — each one recompiles; any whose SQL depends on the *shape* you are
  changing (a renamed or retyped column, a changed grain) breaks rather than
  merely rebuilds.
- **metrics** — a metric depending on a changed column changes value silently.
  This is the dangerous class: nothing errors, the number is just different.
  `query_metrics` before and after and compare.
- **Evidence pages** — a page referencing a removed column fails at build, which
  is CI's problem; a page referencing a *redefined* one renders a wrong number,
  which is nobody's problem until someone acts on it.
- **contracts** — `mdl/mdl.json` and `catalog/openmetadata.json` are published
  contracts. If the change reaches them, an external consumer is affected and the
  change needs to be announced, not just merged.

## When the answer is empty

An empty blast radius means one of three things, and they are not equivalent:

1. Nothing depends on it. Fine — proceed.
2. The graph does not have this node. Usually a brand-new model:
   `pf kg build <group> <project>`, then ask again.
3. **There is no graph.** Then the gate is inert and every edit in this project
   is unverified. The PreToolUse hook says so explicitly when this happens. Build
   the graph before continuing; do not treat silence as safety.

## After a change with real reach

Run the data-level diff, not just the dependency list — `pf tool recce run
<group> <project>` shows whether the numbers actually moved. Dependencies tell
you what recompiles; recce tells you what changed.
