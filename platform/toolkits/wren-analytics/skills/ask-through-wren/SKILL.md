---
name: ask-through-wren
description: Answer a data question conversationally through the project's semantic layer (WrenAI MDL) when no governed metric covers it — read the project's rules and remembered answers, plan one read-only SELECT over MDL model names, run it through the gated road (policy → plan → dry-run → execute → ledger) and reply with the number, the SQL that produced it and its limits. Use when someone asks "how many", "show me", "top N", "compare", "trend", "breakdown", "which rows" about a project's data and `query_metrics` says no metric fits, or asks to remember a validated question for next time. Never for a governed KPI (that is `answer-with-metrics`), never across projects, never with raw SQL against tables.
---
# Ask through Wren

One project, one question, one road. The semantic layer decides what a name
means; the gate decides whether a statement may run; the ledger remembers that
it did. You decide nothing about either.

```
question ─► scope ─► context ─► metric? ─► plan ─► pf tool wren query ─► answer ─► (store)
                      rules · recalled answers · schema        policy · plan · dry-run · execute · ledger
```

## Rules

1. **One project.** Resolve it once (`uv run pf status`, or the session's
   active project). Everything below is scoped to it: the workspace under its
   `mdl/wren/`, its ledger, its warehouse. Another project's tables are not
   visible and are never guessed at. A question that spans sisters goes to the
   `_rollup` project (`duckdb-ops: attach-db`), not here.
2. **A governed number is its metric.** Before planning SQL, `list_metrics` /
   `query_metrics` (`dbt-semantic: answer-with-metrics`). If a metric answers
   the question, use it and stop. If a metric *nearly* answers it, say which
   definition is missing. Recomputing a defined metric in SQL is a bug.
3. **Read before you plan.** `wren_context` (MCP) or
   `uv run pf tool wren context <g> <p> "<question>"` returns the project's
   rules, the remembered questions that resemble this one, and the schema an
   agent may use. A rule outranks a guess; a remembered answer outranks a fresh
   plan when the question is the same.
4. **One read-only SELECT over MDL model names.** Model names as the workspace
   lists them, never `schema.table`. No joins the relationships do not declare.
   A price is never summed, a percentage never averaged; a metric's aggregate
   is what the cube says. For a measure-by-dimension question prefer the cube:
   `wren_cube` (MCP) or `pf tool wren cube <g> <p> --cube <c> --measures <m>
   --dimensions <d> [--time-dimension date:month] [--filter dim:eq:value]`.
   A cube is one base model: combine only its own measures and dimensions.
5. **Only the gate runs it.** `wren_query` / `wren_cube` (MCP) or
   `uv run pf tool wren query <g> <p> "<sql>" --limit N` / `pf tool wren cube`.
   Never `execute_sql_query`, never `wren --sql` or `wren cube query`, never a
   warehouse connection of your own. The gate refuses anything but a read, plans it against the
   LLM-facing manifest, `EXPLAIN`s it read-only, row-limits it and records the
   run. Its refusal is the answer to relay.
6. **Three attempts, then escalate.** A statement the gate refuses comes back
   with the stage and the reason. Fix *that* and try again — at most three
   times for one statement; the ledger counts, not you. The fourth is refused
   with "escalate": report the recorded reasons and stop.
7. **Personal data is absent, not hidden.** Columns classified PII are not in
   the workspace. If a question needs one, the honest answer is that this
   workspace cannot answer it, and why.
8. **Say what you did.** The answer names the model(s) or cube, the planned SQL
   the gate ran, the row limit, and the ledger run id. A number without its
   query is not an answer here.
9. **Remember what was validated.** When the asker confirms the answer, store
   the pair: `uv run pf tool wren store <g> <p> --nl "<question>" --sql "<sql>"`.
   It becomes `mdl/wren/knowledge/sql/<slug>.md`, a tracked file that reaches
   other agents through a pull request, reviewed like code. Store only SQL the
   gate ran successfully.

## The road, step by step

| Step | Do | Owner |
|---|---|---|
| scope | `uv run pf status`; refuse a question about another project | this skill |
| context | `wren_context` / `pf tool wren context` — rules, recalled pairs, schema | `pf.tools.wren_context` |
| metric | `list_metrics`, `query_metrics`; stop if a metric answers | `dbt-semantic: answer-with-metrics` |
| plan | write the SELECT over model names; `pf tool wren plan` to see the expansion if unsure | you, then the engine |
| run | `wren_cube` / `pf tool wren cube` for a cube; `wren_query` / `pf tool wren query --limit N` for SQL | `pf.tools.wren_gate` |
| answer | number + model/cube + planned SQL + limit + run id; truncation stated | this skill |
| store | on confirmation, `pf tool wren store` | `wren memory` |

## When the gate says no

| Stage | Meaning | Do |
|---|---|---|
| `translate` | the cube question names a measure, dimension or operator the cube does not have | re-read the cube in the rules; operators are `eq`, `neq`, `in`, `gt`, `gte`, `lt`, `lte`, … |
| `policy` | not one read-only SELECT | rewrite as a single SELECT; nothing that writes, attaches or configures |
| `plan` | a name the LLM-facing manifest does not know | re-read the schema in the context; a withheld column has no name here |
| `dry_run` | the plan does not compile on the warehouse | the model is not built — `pf seed <g> <p>` is the owner's to run; report it |
| `execute` | the warehouse refused | quote the error; do not retry blindly |
| attempt 4 | the same statement failed three times | escalate with the ledger's reasons |

## What this skill is not for

- A governed KPI, a metric by dimension over time → `dbt-semantic: answer-with-metrics`.
- Profiling raw or staging tables, debugging a load → `duckdb-ops`, `dlt-explore`.
- Anything across sister projects → the roll-up project only.
- Changing a model, a metric or the workspace's rules → `dbt-modeling`,
  `dbt-semantic`, `ontology-design`; the rules are generated from those.

## Operating the workspace (owners, not askers)

```bash
uv run pf tool wren workspace <g> <p> [--index]  # regenerate mdl/wren/ from the manifest, ontology, graph
uv run pf tool wren check <g> <p>                # committed workspace = what the manifest projects? (CI runs --all)
uv run pf tool wren rules <g> <p>                # what an LLM is handed
uv run pf tool wren serve <g> <p>                # Wren's MCP over this workspace, transpile-only
uv run pf tool doctor <g> <p>                    # can the engine plan at all
```

`tools.yaml` → `wren: {hide_roles: [...]}` withholds further roles per group or
project. `groups/<g>/wren/knowledge/rules/*.md` states a rule once for every
sister. Both are reviewed in a pull request, like any other rule.
