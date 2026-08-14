# zenith-de — project context

@kg/context_card.md
@kg/tools_card.md

Group: `zenith`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
<!-- Domain facts an agent cannot derive from the models. Keep it tight. -->
- (none yet)

## The semantic stack
Vocabulary is platform-wide and already loaded in this project's graph before any
data exists — `kg_search` finds concepts, relations and policies on day one.

| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl zenith zenith-de` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap zenith zenith-de` |

A foreign key must be declared with `links={"col": "SomeClass"}`, and the topology
must already relate the two classes — that binding is what makes join conditions
derivable rather than guessed. `pf check` fails on an undeclared join.

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Marts declare `meta.grain`; the semantic layer owns aggregation policy.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
