---
when: Adding or changing Dagster assets, schedules, sensors or partitions.
rules:
  - Assets come from the runtime factory; a project contributes business logic, not wiring.
  - Sister projects run in parallel and each writes its own warehouse — never share a writer.
---

# dagster-orchestrate

The factory builds the asset graph from the project's dbt manifest and annotated
sources. Hand-registering an asset that the factory would have produced creates
two definitions of the same node, and the one that wins depends on import order.
