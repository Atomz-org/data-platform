# commodity-india — project context

@kg/context_card.md

Group: `commodity`. The sister roster lives in the group card above —
do not read a sister's files from here.

## Business rules the graph cannot encode
- This project is market `IN` (`var('market_code')`, the group's `markets` seed):
  landed ₹ = benchmark per market unit × USD/INR × (1 + duty), in the conformed
  `fct_landed_prices_daily` every sister builds (`landed_price_local`,
  `usd_fx_rate`). The benchmark stands in for CIF: no freight, insurance,
  landing charges or GST (ADR-0005).
- Duty rates were verified June 2026 and back-applied to older dates; those rows
  have `is_duty_rate_confirmed = false` (ADR-0001). A duty change is a new dated
  row in `import_duties`; an old row only has its interval closed, its
  rates are never edited.
- `live_cattle` is prohibited (DGFT): it keeps its price, never a landed price.
- Nine commodities have no free feed; their levels are the group's
  `indicative_prices` seed, refreshed by appending a row with a new `as_of_date`.
- MCX contracts (GOLDM … ALUMINI, ZINCMINI) are landed equivalents per quote
  basis and lot, not MCX quotes. Zinc has no usable free feed — Yahoo's
  `ZNC=F` is an untraded COMEX series — so it stays on the LME indicative level.
- Futures do not settle at weekends: a Monday freshness breach on
  `futures_prices` is the calendar, a midweek one is the feed.
- dlt Core lands the raw stage (datasets `yahoo_finance`, `gold_api`) through the
  group's connectors (`commodity_shared`); the catalog is the group's
  `commodities` seed, not a source. dbt stages it from there. A source is a declarative `rest_api`
  config where the endpoint allows and `RESTClient` where it does not (ADR-0004).

## The semantic stack
| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl commodity commodity-india` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap commodity commodity-india` |

A foreign key must be declared with `links={"col": "SomeClass"}`, and the topology
must already relate the two classes. `pf check` fails on an undeclared join.

## Conventions
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Prices use the group's `unit_price` role, never `money_amount` (ADR-0002).
  Means are ratio metrics (ADR-0003). Group price metrics by commodity.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
