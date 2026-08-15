# OpenMetadata — the catalogue for acme/acme-rollup

The catalogue is where someone who does not read YAML finds out what a table
means. This project publishes into it automatically.

```bash
pf tool openmetadata payload acme acme-rollup   # what would be published
pf tool openmetadata sync acme acme-rollup      # regenerate the artefacts
pf tool openmetadata ingest acme acme-rollup    # run the dbt ingestion
pf tool doctor acme acme-rollup                 # can it actually reach the server
```

## What publishes what

| Source | Becomes |
|---|---|
| `platform/.../concepts.yaml` | Glossary terms, with identity and properties |
| ontology roles | `PlatformRole` tags; PII roles also get `PII.Sensitive` |
| topology relations | `relatedTerms` between glossary terms |
| policy layer | Glossary terms describing each constraint |
| dbt `target/*.json` | Tables, columns and column-level lineage |
| recce checks | Test cases carrying the review verdict |

Tables and lineage come from `metadata ingest-dbt`, not from us. We publish what
they *mean*; dbt publishes what they *are*.

## It is a projection, not a sync

Nothing is read back. Edit `concepts.yaml` and re-run — a change made in the
catalogue UI is overwritten on the next publish, on purpose. The ontology is
canonical and stays in git where `pf check` and the gate can judge it.

## Configuration

`OPENMETADATA_JWT_TOKEN` must be set wherever ingestion runs; it is a credential
and is never written into a generated file. Host and service name come from
`tools.yaml`, defaulting to `http://localhost:8585` and `acme_acme-rollup`.
