---
name: find-source
description: Discover and scaffold a new dlt source. Use when the data needed does not exist in the warehouse yet.
---
# Find and scaffold a source

There is no hosted connector catalogue in dlt Core. Work down this ladder and
stop at the first tier that fits.

1. **Verified sources.** `dlt init <source> duckdb` pulls from dlt's maintained
   repo (stripe, salesforce, hubspot, github, notion, zendesk, sql_database,
   filesystem, …). Check `registry/` first — it lists what this platform has used.
2. **OpenAPI spec.** If the API publishes one, `dlt-init-openapi <name> --url <spec>`
   generates a full `rest_api` source. This covers most of the long tail.
3. **Hand-rolled `rest_api`.** Configure `client`, `resources`, `paginator` and
   `incremental` explicitly. Use `read-file` (duckdb-ops) to profile a sample
   payload before writing the config.

Then, always:
- Place the source in `src/<project>/sources/<name>.py`.
- Apply `@annotate(...)` — an unannotated resource fails `pf check`.
- Commit the connector back to `platform/toolkits/dlt-ingest/registry/<name>.yaml`
  so the next company inherits it.
- Never put credentials in the source file. Use `secrets_update_fragment`.

## After the first load: propose the ontology

A source that has landed but is not in the vocabulary is invisible to dbt, Wren,
the BI layer and every agent. Close that gap immediately:

```bash
pf seed <group> <project>                        # land the data
pf semantic scan <group> <project> --source <n>  # induce a proposal
```

Then use the `steward-ontology` skill. The scan proposes; a human decides. Do not
approve your own proposal without reading the evidence on each axiom.
