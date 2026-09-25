# requirement-pipeline — a Confluence requirement, built end to end

Orchestrates the other toolkits for one business requirement: Confluence →
`spec.yaml` → dlt raw → dbt staging / intermediate / marts → MetricFlow →
Evidence, with Dagster assets and the OpenMetadata catalogue over all of it.

- The spec is the contract. Extract once, cite the page for every field, and
  turn every unknown into an open question.
- Reuse before build. A second definition of an existing metric is a bug.
- Delegate every layer to the toolkit skill that owns it; `references/skill-map.md`
  is the routing, and every toolkit skill has a place in it or an explicit hand-back.
- Rules in intermediate, grain in marts, aggregation in metrics, nothing in pages.
- Stop at the three checkpoints: spec, landed data, hand-off.
