---
name: add-a-market
description: Add a country to the commodity family as its own sister project — one row in the market registry, one scaffold, the market's own seeds, the conformed models copied unchanged — then seed it and register it with the roll-up.
---
# Add a market

A market is a tenant: one jurisdiction, one currency, one customs regime, one
warehouse. Everything that is the same for every market is already the
group's; everything that is this market's alone goes in its project. Nothing
is copied from another sister's seeds — those are another country's facts.

## 1. Register the market (`groups/commodity`)

- Append a row to `shared/transform/seeds/markets.csv`: `market_code` (ISO
  3166 alpha-2, the tenant key), `market_name`, `country_code`,
  `currency_code` (what a landed price is expressed in), `home_exchange`,
  `timezone`, `project` (`commodity-<cc>`). The roll-up reads this row to know
  the sister exists and what currency she reports in.
- If the market's currency is new, it needs a Yahoo fix (`<CCY>=X`); nothing
  else. If a commodity the market cares about is not in `commodities.csv`, run
  the `add-a-commodity` skill first.

## 2. Scaffold the project

    uv run pf new-project commodity commodity-<cc>

Then, in the new project:

- `src/commodity_<cc>/catalog.py`: `MARKET = market("<CC>")`,
  `COMMODITIES = commodities()` (or `commodities(tracked=[...])` for a
  subset), `FX_CURRENCIES` starting with `MARKET.currency_code`.
- `src/commodity_<cc>/sources/yahoo_finance.py` and `gold_api.py`: copy a
  sister's — they are annotations over the group connectors
  (`commodity_shared.yahoo_finance`, `commodity_shared.gold_api`) and contain
  no market logic. `seed.py` likewise, with GROUP/PROJECT changed.
- `transform/dbt_project.yml`: `vars: market_code: <CC>`, the group macros on
  `macro-paths`, `seeds: commodity_shared: +schema: reference`. `packages.yml`
  already carries the group package after bootstrap.

## 3. The market's own seeds (`transform/seeds`)

Same names in every sister, different content in each — the conformed models
`ref()` them by these names:

- `market_units.csv` — the unit the local market quotes each commodity in
  (`commodity_id, market_unit`). Same `dimension` as the benchmark's quote
  unit or `assert_units_convert_within_one_dimension` fails.
- `import_duties.csv` — the customs regime as dated intervals: `tariff_id,
  commodity_id, market_country, valid_from, valid_to, confirmed_from,
  is_import_prohibited, effective_duty_rate, duty_basis`, plus whatever
  component columns the regime has (India's BCD/AIDC/SWS; the US has none).
  A rate change is a new dated row; `confirmed_from` is the first date the
  rate is known to have applied (ADR-0001 in commodity-india).
- Exchange contracts, retail conventions, anything else local: this market's
  seeds, this market's marts under `models/marts/<cc>/`.

## 4. The conformed models — copy, do not adapt

`models/intermediate/*`, `models/marts/core/*`, `models/semantic/*` and
`models/utils/*` are identical in every sister. Copy them from a sister
byte-for-byte; the group test `test_conformed_models_are_identical` fails if
they drift. They read the market through `var('market_code')` and the
`markets` seed, and the market's facts through the seed names above. A USD
market needs no FX row: the model uses a rate of 1.

## 5. Seed, check, register

    uv run pf seed commodity commodity-<cc>
    uv run pf check
    uv run pf bootstrap commodity commodity-<cc>

Then add the sister to the roll-up's roster
(`projects/commodity-rollup/src/commodity_rollup/roster.py`) and to
`group.yaml` (`resources.warehouses`, `resources.catalog_services`), and
re-seed the roll-up. Read the new project's `kg/context_card.md` **Known gaps**
before calling it done.
