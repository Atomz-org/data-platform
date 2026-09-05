# OpenMetadata — the catalogue for hospital/mental-health

The catalogue is where someone who does not read YAML finds out what a table
means. This project publishes into it automatically.

```bash
pf tool openmetadata payload hospital mental-health   # what would be published
pf tool openmetadata sync hospital mental-health      # regenerate the artefacts
pf tool openmetadata ingest hospital mental-health    # database, then dbt
pf tool openmetadata pull hospital mental-health      # owners' edits, as a proposal
pf tool doctor hospital mental-health                 # can it actually reach the server
```

## What publishes what

| Source | Becomes |
|---|---|
| production warehouse | Schemas, tables, columns — `catalog/ingestion/database.yaml` |
| dbt `target/*.json` | Models, column-level lineage, tests, owners — `catalog/ingestion/dbt.yaml` |
| `platform/.../concepts.yaml` | Glossary terms, with identity and properties |
| ontology roles | `PlatformRole` tags; PII roles also get `PII.Sensitive` |
| topology relations | `relatedTerms` between glossary terms |
| policy layer | Glossary terms describing each constraint |
| knowledge graph metrics | OpenMetadata metrics, with their expressions |
| recce checks | Test cases carrying the review verdict |

**Order matters and is enforced.** The database pass catalogues tables; every
other row above describes tables. Run dbt ingestion alone against an empty
service and it has nothing to attach to — which is what this project did before
`catalog/ingestion/` existed, publishing a vocabulary over zero tables.

The catalogue points at **production**, never at your DuckDB file. The
connection comes from `pf.runtime.targets`, so the warehouse this project
deploys to and the one it catalogues cannot disagree.

## Owners can edit, in one direction with a return path

Nothing is read back automatically. Edit `concepts.yaml` and re-run — a change
made in the catalogue UI is overwritten on the next publish, on purpose. The
ontology is canonical and stays in git where `pf check` and the gate can judge
it.

That would make the catalogue read-only for the people who know the most, so
there is a proposal channel:

```bash
pf tool openmetadata pull hospital mental-health
```

reads back descriptions, owners and column documentation, diffs them against
`contracts/annotations.yaml`, and writes the differences to
`catalog/owner-edits.yaml`. Nothing is applied. Move a line across by hand, in a
pull request, so a change to what a column means gets the review any other such
change gets.

## Configuration

`OPENMETADATA_JWT_TOKEN` must be set wherever ingestion runs; it is a credential
and is never written into a generated file. Host and service name come from
`tools.yaml`, defaulting to `http://localhost:8585` and `hospital_mental-health`.
