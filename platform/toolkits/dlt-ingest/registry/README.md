# Local connector registry

The dlt Core replacement for dltHub's hosted connector catalogue. Every source an
agent builds gets committed here, so the next company inherits it.

One YAML per source: `name`, `kind` (verified|openapi|rest_api), `spec_url` or
`dlt_init_name`, the ontology `concept` each resource maps to, default
`incremental` cursor, and the secrets keys it needs (names only — never values).
