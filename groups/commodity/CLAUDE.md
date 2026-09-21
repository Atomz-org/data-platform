# commodity — group context

@kg/group_card.md

Sister projects under `projects/` share this ontology instance, the conformed
dimensions in `shared/transform`, and group-level metrics. They have **separate
warehouses and run in parallel**.

## Business rules the graph cannot encode
- A price is a `unit_price`, never a `money_amount`: not additive. A mean is a
  sum ÷ count ratio metric within one commodity; never aggregate across
  commodities or markets.
- Convert minor-unit quotes first (`USX`, `GBX`) with `to_major_currency`, then
  units, then FX. Unit factors live in the shared `units_of_measure` seed.
- A sister is a **market**: one `markets` row, one currency, one customs
  regime, one warehouse (`add-a-market`). The catalog, units, indicative
  levels and connectors are the group's; a market's units, duty and contracts
  are its own seeds under conformed names (`market_units`, `import_duties`).
- The conformed marts and semantic layer are identical SQL in every sister;
  change them everywhere or nowhere. The roll-up refuses a sister that differs.
- dlt Core lands raw only; dbt owns staging (`pf gen-staging`), conversion and
  grain. Never transform in a dlt resource; never join in staging.

## Cross-entity work
Only `commodity-rollup` may read sister data, and only via ATTACH READ_ONLY.
Never read a sister project's files from another project.
