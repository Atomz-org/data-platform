---
type: Vendor Upstream
title: Recce
description: 'dbt PR review: the empirical half of impact analysis'
resource: https://github.com/DataRecce/recce
tags:
- vendor
- reference
- Apache-2.0
status: stable
sources:
- id: recce:recce/cli.py
  resource: https://github.com/DataRecce/recce
  title: recce/cli.py
- id: recce:recce/constants.py
  resource: https://github.com/DataRecce/recce
  title: recce/constants.py
- id: recce:recce/summary.py
  resource: https://github.com/DataRecce/recce
  title: recce/summary.py
- id: recce:recce/mcp_server.py
  resource: https://github.com/DataRecce/recce
  title: recce/mcp_server.py
---

# Recce

The knowledge graph answers what *could* break when a model changes. Recce answers what *did* change, by diffing the built warehouse against a baseline. Those are different questions and the platform had only the first: `pf impact` reports a blast radius from lineage, with no way to say whether the numbers actually moved. Recce closes that, and it closes it against dbt's own artefacts rather than a parallel model of them.

## Adopted

- **recce/cli.py** (data) -> platform/src/pf/tools/recce.py
  We invoke the CLI as a subprocess — `recce run`, `recce server` — and both the subcommands and their flags are part of that contract. A renamed option is a silent behaviour change here, which is why this is `data` and not `shape`.
- **recce/constants.py** (data) -> platform/src/pf/tools/recce.py
  RECCE_CONFIG_FILE ("recce.yml") is the filename our bootstrap step writes. If upstream renames it, our generated config stops being read and every check silently reports zero.
- **recce/summary.py** (shape) -> platform/src/pf/tools/recce.py
  `recce run --summary` emits the markdown we attach to the Dagster run and to `pf pr`. We consume the file, not the function.
- **recce/mcp_server.py** (shape) -> platform/src/pf/tools/recce.py
  Recce serves its own MCP tools. Noted rather than adopted: `pf mcp` already fronts the graph, and two MCP servers answering overlapping questions is how an agent gets two different answers.

## Declined

- **recce_cloud/ and the `--cloud` flag**
  State would leave the machine. This platform is local-first and every warehouse is a file on disk; a cloud round-trip for diff state is a data-residency decision, not a convenience, and it is not one an agent should make. `pf tool recce` never passes --cloud.
- **`top_k_diff` for category drift**
  It cannot answer the question. The task returns parallel arrays (`values`, `counts`) and recce compares results with `DeepDiff(..., ignore_order=True)`, so renaming a category moves a count between slots while both arrays stay equal as multisets — the drift is invisible. Verified against a real rename: the check ran green while `starter` had become `basic`. We emit a `query_diff` keyed on the category instead, which returns one row per value and surfaces the same rename as a row present on one side only. The interactive UI renders the arrays side by side, so a human still sees it there; it is the headless summary that goes quiet, and that is the one CI reads.
- **`recce init` for config generation**
  It is interactive. Our recce.yml is generated from the ontology roles we already have — a natural key is a primary key, a money_amount is worth a value diff — so the config derives from the same declaration everything else does rather than from a wizard.
