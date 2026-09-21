# commodity-us — project context

@kg/context_card.md

Group: `commodity`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
- Market `US` (`var('market_code')`, the group's `markets` seed). It prices in
  USD, so `usd_fx_rate` is 1 and the conformed landed price is **import
  parity**: benchmark per market unit × (1 + duty). It moves only for the
  Section 232 metals, lumber and the dutiable oils and grains.
- Duty follows ADR-0001: Section 232 dated from its proclamations, MFN as
  printed, specific duties converted above ~1% and nil below; origin-dependent
  tariffs (IEEPA, over-quota, AD/CVD) are **not** modelled and those rows have
  no `confirmed_from`. `duty_basis` states each simplification.
- Copper is the refined-cathode benchmark, outside Section 232 copper;
  aluminium and steel carry 50% since 4 June 2025. Nothing is prohibited.
- US contracts (GC, HG, CL, ZW, …) are import-parity equivalents per quote
  basis and lot, from the benchmark. Base metals are quoted per pound here.
- Futures do not settle at weekends: a Monday freshness breach is the
  calendar, a midweek one is the feed.
- dlt Core lands `yahoo_finance` and `gold_api` through the group's connectors
  (`commodity_shared`); the catalog is a seed, not a source.

## The semantic stack
| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl commodity commodity-us` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap commodity commodity-us` |

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Prices use the group's `unit_price` role, never `money_amount`. Means are
  ratio metrics. Group price metrics by commodity.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
