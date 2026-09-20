# commodity-us — project context

@kg/context_card.md

Group: `commodity`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
- This project is market `US` (`var('market_code')`, the group's `markets` seed).
  It prices in USD, so `usd_fx_rate` is 1 and the conformed landed price is
  **import parity**: benchmark per market unit × (1 + duty). For a duty-free
  commodity that is the benchmark itself; the number only moves for the
  Section 232 metals, lumber and the dutiable oils and grains.
- Duty is modelled as written in `import_duties.duty_basis` and decided in
  ADR-0001: Section 232 rates dated from their proclamations; MFN ad valorem
  as printed; specific (cents/kg) duties converted at a stated benchmark price
  when above ~1%, nil below; IEEPA reciprocal tariffs, over-quota TRQ rates and
  antidumping duties depend on origin and are **not** modelled. A row with no
  `confirmed_from` says so through `is_duty_rate_confirmed = false`.
- Copper is the refined-cathode benchmark (COMEX HG), which Section 232 copper
  does not cover; aluminium and steel do carry 50% since 4 June 2025.
- Nothing is prohibited. Mexican live-cattle imports have been suspended on
  animal-health grounds since 2025; that is a health measure, not a tariff, and
  is not modelled.
- US exchange contracts (GC, HG, CL, ZW, ...) are import-parity equivalents per
  quote basis and lot, built from the benchmark — not separate quotes. Base
  metals are quoted per pound here; the LME metals with no free feed have no
  US contract and stay on the group's indicative level.
- Futures do not settle at weekends: a Monday freshness breach on
  `futures_prices` is the calendar, a midweek one is the feed.
- dlt Core lands the raw stage (datasets `yahoo_finance`, `gold_api`) through the
  group's connectors (`commodity_shared`); the catalog is the group's
  `commodities` seed, not a source. dbt stages it from there.

## The semantic stack
| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl commodity commodity-us` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap commodity commodity-us` |

A foreign key must be declared with `links={"col": "SomeClass"}`, and the topology
must already relate the two classes. `pf check` fails on an undeclared join.

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Prices use the group's `unit_price` role, never `money_amount`. Means are
  ratio metrics. Group price metrics by commodity.
- The conformed models (`intermediate/`, `marts/core/`, `semantic/`, `utils/`)
  are identical in every sister — change them in all or in none.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
