# Wren — conversational analytics for acme/acme-rollup

`mdl/mdl.json` is this project's semantic layer in MDL, generated from the
knowledge graph by `pf bootstrap` — never hand-edited. Beside it, `mdl/wren/` is
the workspace Wren's CLI reads, generated from the same inputs:

| Path | What | Tracked |
|---|---|---|
| `mdl/wren/wren_project.yml` | name, catalog, schema, data source | yes |
| `mdl/wren/target/mdl.json` | the manifest an LLM may see: PII and `hide_roles` columns withheld | no |
| `mdl/wren/knowledge/rules/NN-*.md` | scope, concepts and roles, metrics and cubes, policies, enumerations | yes |
| `mdl/wren/knowledge/sql/*.md` | questions answered before, as `wren memory store` writes them | yes |
| `mdl/wren/.wren/memory/` | the derived index (`wren[memory]`, LanceDB) | no |

Every `wren` call this project makes runs inside that workspace with
`WREN_PROJECT_HOME` and `WREN_HOME` pointed at it. Nothing is read from
`~/.wren`, and nothing of another project is visible.

```bash
pf tool wren workspace acme acme-rollup       # (re)generate the workspace; --index for memory
pf tool wren check acme acme-rollup           # is the committed workspace what the manifest projects?
pf tool wren context acme acme-rollup "<q>"   # rules + remembered questions + schema, for one question
pf tool wren plan acme acme-rollup "<sql>"    # expand SQL through the MDL, no warehouse
pf tool wren query acme acme-rollup "<sql>"   # policy → plan → dry-run → execute → ledger
pf tool wren cube acme acme-rollup --cube <c> --measures <m> --dimensions <d>   # a cube question, same road
pf tool wren api acme acme-rollup             # the API behind the Evidence "Ask the data" page (or --all)
pf tool wren store acme acme-rollup --nl "<q>" --sql "<sql>"   # remember a validated answer
pf tool doctor acme acme-rollup               # is the engine actually usable
```

## The road every question takes

`pf tool wren query` and `pf tool wren cube` (the `wren_query` and `wren_cube`
MCP tools) never run what they are given. A cube question is first translated
into one `SELECT` by the engine. The gate checks the statement is one read-only
`SELECT`, plans it through the
LLM-facing manifest, `EXPLAIN`s the plan on this project's warehouse read-only,
executes it row-limited, and appends the outcome — refused or not — to
`groups/acme/loop-ledger.json` as a `wren-query` run. A statement refused
three times is refused with "escalate". `loop-constraints.md` applies.

## MCP

`.mcp.json` registers `wren serve mcp --project mdl/wren --no-connect`: Wren's
own context tools (models, cubes, `dry_plan`) over this workspace, in
transpile-only mode. Execution goes through `pf`'s `wren_query`, which is the
gated road above — never through a second connection.

## There is no Wren web UI

Upstream's Docker chat-first BI app is `legacy/v1` ("Wren GenBI Classic"). Current
WrenAI is a CLI plus `wren serve`, which serves **MCP**, not a web page. The
semantic surface you look at is `pf ui` -> **Semantics**, which reads the same
manifest. Nothing is being iframed, because there is nothing to iframe.
