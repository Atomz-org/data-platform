## commodity — group index

**Sister projects (1):** `commodity-india`
**Ontology classes in scope:** Product, Currency, Location

Sisters share the ontology, conformed dimensions and group metrics, but have separate warehouses and run in parallel. Cross-entity questions are answered only in the `<group>-rollup` project, which attaches sister databases READ_ONLY.

**Do not read a sister project's files from here.** If you need cross-entity data, use the rollup project.
