# ADR-0001: the sisters are the raw stage

**Status:** accepted · 2026-09-20

## Context

The platform's reference roll-up attaches sister warehouses READ_ONLY inside a
Dagster asset and unions one hardcoded mart into its own database. Nothing
downstream of that union had a staging model, an annotation, a place in the
knowledge graph or a monitor, and the asset only knew about a revenue table.
A commodity roll-up needs the same lineage every sister has — raw → `stg_` →
marts — and it needs to refuse a sister whose marts have drifted, because a
union over columns that merely share a name is the failure the family's
CLAUDE.md warns about.

## Decision

The sisters' conformed marts are this project's **raw stage**, landed by dlt
like any other source:

- `commodity_shared.sisters.read_mart` attaches each sister READ_ONLY to a
  scratch DuckDB connection, checks that the mart exists in every sister with
  one column set, and streams it as Arrow. A missing file, a missing mart or a
  differing column set is an error naming the sister and the columns. The
  check runs before any row is read.
- The `sisters` dlt source (`sources/sisters.py`) lands the union as
  `sisters.landed_prices`, `write_disposition="replace"`: it is a snapshot of
  what the sisters have built, not an event stream. The natural key is
  market-qualified (`IN:gold:2026-09-16`) because `price_id` repeats across
  markets.
- `pf gen-staging` produces `stg_sisters__landed_prices` from the annotation,
  and the marts read that. Lineage in Dagster runs sister mart → dlt resource →
  staging → marts, across code locations.
- The platform's roll-up asset stays, generalised: `build_definitions(...,
  rollup_tables=CONFORMED_TABLES)` declares which sister marts this project
  depends on, and the asset checks their shapes agree before the ingest runs.
  It writes nothing; what the roll-up makes of its sisters is dbt's.

## Consequences

- The roll-up is a normal project to every platform tool: annotations,
  monitors, the graph, the card, recce, the MDL projection all work unchanged.
- Adding a market is a roster line and a `markets` row; the roll-up needs no
  new mapping because the sisters already agree on shape by construction.
- A sister that changes a conformed column breaks the roll-up's seed with the
  column named, which is the intended place for that to surface.
- Comparisons are made in USD per the benchmark's quote unit, undoing each
  sister's FX at the rate she applied. The benchmark cancels, and what remains
  — duty and FX timing — is what a market adds. That is presented as an
  import-parity premium and as a spread to the cheapest market, never as a
  trading signal.
