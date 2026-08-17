---
name: context-budget
description: Report and repair what this project spends on always-on context — cards, CLAUDE.md, routing, plugins, MCP tools.
disable-model-invocation: "yes"
---

# Context budget

The guide's advice for large codebases is "limit scope". This platform does it
structurally instead: a fixed always-on preamble, budgeted and enforced, plus
graph queries in place of file reads. This command audits that machinery.

## 1. The enforced budget

```bash
uv run pf tokens          # exits non-zero if any card is over
```

Reports every project's `kg/context_card.md` and `CLAUDE.md`, each group card,
`ROUTING.md` and `VENDOR-CARD.md` against its budget, and the worst-case session
preamble total. **Over budget is a build failure, not a warning** — every session
pays it for the whole life of the project.

To repair an over-budget card, regenerate rather than trim by hand:

```bash
uv run pf kg build <group> <project>
uv run pf kg card  <group> <project>
```

If it is still over after regeneration, the project has genuinely outgrown the
card and the fix is fewer, better entries — not a bigger budget.

## 2. What the session loads beyond the cards

```bash
claude plugin list
claude plugin details <plugin>     # component inventory + projected token cost
```

Every enabled plugin contributes skill descriptions to every request. A toolkit
that this project will never use (Snowflake macros in a DuckDB-only project) is
pure overhead — disable it in `.claude/settings.json` rather than tolerating it.

Same question for MCP: the `pf` server registers 23 tools. Their schemas ride in
context unless the client defers them.

## 3. Spend it on the graph, not on files

The cheapest large-context strategy here is not to load the context:

| Instead of | Do |
|---|---|
| reading four models to find a dependency | `kg_neighbors` |
| grepping for where a concept is used | `kg_search` |
| reading downstream models to judge a change | `impact_analysis` |
| reading a whole sister project | never — it is a gate violation |

## 4. When a session is already too full

- `/clear` between unrelated tasks. Context carried across two tasks makes the
  second one worse, not better.
- Prefer one project per session: `pf work <group> <project>` sets cwd so the
  gate, the MCP server and the card all resolve to the same entity.
- For a genuinely repo-sized question, hand it to a bigger window rather than
  compacting this one: `/gemini-analyze`.

## 5. Report

Current preamble total, each artefact against its budget, plugins enabled versus
plugins used, and one recommendation per overspend. Say what to remove; do not
remove it as part of this command.
