# acme-eu — project context

@kg/context_card.md

Group: `acme`. The sister roster lives in the group card — do not read a sister's files from here.

## Business rules the graph cannot encode
<!-- Domain facts an agent cannot derive from the models. Keep it tight. -->
- (none yet)

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Marts declare `meta.grain`; the semantic layer owns aggregation policy.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
