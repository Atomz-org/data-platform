## acme — group index (generated 2026-08-23)

**Sister projects (3):** `acme-eu`, `acme-rollup`, `acme-us`
**Ontology classes in scope:** Customer, Organization, Subscription, Payment, Usage, Product

Sisters share the ontology, conformed dimensions and group metrics, but have separate warehouses and run in parallel. Cross-entity questions are answered only in the `<group>-rollup` project, which attaches sister databases READ_ONLY.

**Do not read a sister project's files from here.** If you need cross-entity data, use the rollup project.
