# commodity-india — project context

@kg/context_card.md

Group: `commodity`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
- Market `IN` (`var('market_code')`, the group's `markets` seed): landed ₹ =
  benchmark per market unit × USD/INR × (1 + duty), in the conformed
  `fct_landed_prices_daily`. The benchmark stands in for CIF (ADR-0005).
- Duty rates verified June 2026 and back-applied; earlier rows carry
  `is_duty_rate_confirmed = false` (ADR-0001). A change is a new dated row in
  `import_duties`; old rows only have their interval closed.
- `live_cattle` is prohibited (DGFT): a price, never a landed price.
- Nine commodities have no free feed; their levels are the group's
  `indicative_prices` seed, refreshed by appending a newer `as_of_date`.
- `fct_mcx_lot_equivalents_daily` is a landed equivalent, not an MCX quote;
  MCX's own settlement is the `mcx` dataset and `marts/mcx/` (ADR-0006). Zinc's
  landed level stays on LME indicative (`ZNC=F` is untraded).
- MCX prices are ₹ per each code's quote basis (GOLD per 10 g, GOLDPETAL per
  1 g): compare codes by return, never by price. One job per commodity in
  `mcx_products`; pause in Dagster (`docs/mcx.md`).
- Futures do not settle at weekends: a Monday freshness breach is the
  calendar, a midweek one is the feed.
- dlt Core lands `yahoo_finance` and `gold_api` through the group's connectors
  (`commodity_shared`), and `mcx` through this project's `mcx_feed`; the
  catalog is a seed, not a source (ADR-0004).

## The semantic stack
| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl commodity commodity-india` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap commodity commodity-india` |

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Prices use the group's `unit_price` role, never `money_amount` (ADR-0002).
  Means are ratio metrics (ADR-0003). Group price metrics by commodity.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
