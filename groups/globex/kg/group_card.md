## globex — group index (generated 2026-08-13)

**Sister projects (2):** `globex-core`, `globex-eu`
**Ontology classes in scope:** Customer, Order, Payment, Refund, Product, Location

Sisters share the ontology, conformed dimensions and group metrics, but have separate warehouses and run in parallel. Cross-entity questions are answered only in the `<group>-rollup` project, which attaches sister databases READ_ONLY.

**Do not read a sister project's files from here.** If you need cross-entity data, use the rollup project.
