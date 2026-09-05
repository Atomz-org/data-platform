# hospital — group context

@kg/group_card.md

Sister projects under `projects/` share this ontology instance, the conformed
dimensions in `shared/transform`, and group-level metrics. They have **separate
warehouses and run in parallel**.

## Business rules the graph cannot encode
<!-- Add durable, entity-wide rules here. Keep it short: this loads every session. -->
- The conformed diagnosis vocabulary (Diagnosis class, ICD-10 groups per
  CSO Ireland HRA71) is the group-wide bridge between clinical facts and
  population benchmarks. A future sister (e.g. an HMS operational entity)
  must map its diagnosis labels into the same groups, not invent parallel ones.
- Mental-health data is special-category under the GDPR / EU AI Act lens even
  when synthetic; anything predictive built on episode outcomes lands in the
  high-risk bucket — declare AIR controls before building it.

## Cross-entity work
Only the `<group>-rollup` project may read sister data, and only via ATTACH READ_ONLY.
Never read a sister project's files from another project.
