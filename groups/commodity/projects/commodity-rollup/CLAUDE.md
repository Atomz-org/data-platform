# commodity-rollup — project context

@kg/context_card.md

Group: `commodity`. Sister projects: commodity-india, commodity-us — the roster
is `src/commodity_rollup/roster.py`, one alias per market. This is the only
project in the family that may read sister data, and only READ_ONLY.

## Business rules the graph cannot encode
- The raw stage is the sisters: dlt reads every sister's conformed
  `fct_landed_prices_daily` READ_ONLY and lands the union as `sisters.landed_prices`
  (ADR-0001). The read is refused before a row moves if any sister's columns
  differ or her mart is missing — a wrong shape here is a wrong number on the
  board, so it fails instead.
- Markets compare only on the benchmark's footing: USD per the commodity's
  quote unit, with the sister's own FX undone at the rate she applied and her
  market unit repriced with the group's factors. Never compare
  `landed_price_local` across markets; the currencies differ.
- The import-parity premium is what a market adds over the benchmark: its duty,
  plus FX timing where a fix was carried forward. It is the duty regime made
  visible, not a trading signal.
- A registered market whose sister has not seeded fails
  `assert_every_registered_market_reports`; the roll-up does not quietly omit a
  country.
- Prices are `unit_price`, never summed. Every mean is a ratio, grouped by
  commodity and market.
- The catalog and market registry are the group's seeds, built here too; the
  roll-up adds no commodity and no market of its own.

## The semantic stack
| Ask | Command |
|---|---|
| What relates to what | `pf semantic topology` |
| What must hold, and what enforces it | `pf semantic policy` |
| BI / WrenAI projection | `pf semantic mdl commodity commodity-rollup` → `mdl/mdl.json` |
| Re-run every generated artefact | `pf bootstrap commodity commodity-rollup` |

## Conventions
- `pf run-all commodity` seeds every sister in parallel, then this project.
  Seeding this project alone reads whatever the sisters last built.
- Every dlt resource is annotated (`@annotate`) before any model is written.
- Ask the graph before reading files: `kg_search`, `kg_neighbors`, `kg_path`.
- Run `impact_analysis` before changing a column, a model or a metric.
