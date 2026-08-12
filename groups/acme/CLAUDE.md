# acme — group context

@kg/group_card.md

Sister projects under `projects/` share this ontology instance, the conformed
dimensions in `shared/transform`, and group-level metrics. They have **separate
warehouses and run in parallel**.

## Business rules the graph cannot encode
<!-- Add durable, entity-wide rules here. Keep it short: this loads every session. -->
- (none yet)

## Cross-entity work
Only the `acme-rollup` project may read sister data, and only via ATTACH READ_ONLY.
Never read a sister project's files from another project.
