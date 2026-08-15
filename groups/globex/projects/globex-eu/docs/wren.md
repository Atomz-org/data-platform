# Wren — semantic layer for globex/globex-eu

`mdl/mdl.json` is this project's semantic layer in MDL, the interchange format a
BI or text-to-SQL layer consumes without being told our internals. It is
generated from the knowledge graph by `pf bootstrap` — never hand-edited.

```bash
pf tool wren mdl globex globex-eu          # what the manifest contains
pf tool wren plan globex globex-eu "<sql>" # expand SQL through the MDL
pf tool wren query globex globex-eu "<sql>"
pf tool doctor globex globex-eu            # is the engine actually usable
```

## There is no Wren web UI

Upstream's Docker chat-first BI app is `legacy/v1` ("Wren GenBI Classic"). Current
WrenAI is a CLI plus `wren serve`, which serves **MCP**, not a web page. The
semantic surface you look at is `pf ui` -> **Semantics**, which reads this same
manifest. Nothing is being iframed, because there is nothing to iframe.

## Against the review

`pf ui` -> **Workspace** joins this manifest to Recce's recorded diff on the
model behind each entity, so "fct_revenue moved" is read as which semantic
entity changed and which ontology roles ride on it. It needs the `recce` tool on
as well; both are on by default for a new group.
