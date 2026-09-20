---
name: add-a-commodity
description: Add a tracked commodity in two halves, the group half (catalog row or indicative level, unit, classes, annotation roles) and the sister half (market unit, duty, contract lot), then seed every sister and read the cards.
---
# Add a commodity

Two halves. The group half is shared vocabulary; a sister never repeats it.
The sister half is one market's facts; the group never holds them.

## Group half (`groups/commodity`)

- **Catalog row.** One line in `shared/transform/seeds/commodities.csv`:
  `commodity_id`, name, category, segment, `quote_unit`, exchange, then either
  a `yahoo_symbol` (daily futures candles) or, for a precious metal, a
  `spot_symbol` too (the gold-api backup). Every sister builds this seed and
  reads it from Python (`commodity_shared.catalog`), so one row is fetched,
  modelled and priced in every market at once.
- **No free feed.** Leave both symbols empty and append a row to the group's
  `indicative_prices` seed (`commodity_id`, `as_of_date`, `price`,
  `currency_code`, `quote_unit`, `benchmark`). A benchmark level is the same in
  every market, so it lives here. Its `quote_unit` must equal the catalog's
  (`assert_indicative_prices_use_the_catalog_unit`). Refresh by appending a
  newer `as_of_date`, never by overwriting a past level.
- **Unit.** The benchmark's `quote_unit` code must exist in
  `shared/transform/seeds/units_of_measure.csv` with a `dimension` (mass,
  volume_oil, energy, volume_timber) and a `base_units_per_unit` in that
  dimension's base unit. A new dimension is also a new value in the
  `accepted_values` test in `_units_of_measure.yml`. Every sister builds this
  seed from the group package, so one row here reaches all of them.
- **Classes.** `ontology/extension.yaml` already declares `Commodity`
  (identity `commodity_id`, required `quote_unit`) and `PriceObservation`
  (identity `quote_id`; required `commodity_id`, `close_price`,
  `currency_code`, `traded_at`), related MANY_TO_ONE by
  `price_observation_of_commodity`. A new commodity is new rows of those
  classes, not a new class. Extend the ontology only for a new kind of thing.
- **Annotation roles.** Every price resource carries `natural_key`,
  `foreign_key` with `links={"commodity_id": "Commodity"}`, `unit_price`,
  `currency_code`, `event_time`, and `unit_of_measure` where the row states
  its unit. The link is what puts the edge from the price to the commodity in
  the graph, and `pf check` fails on a link to a class the topology does not
  relate.

## Sister half (`projects/<sister>`)

- **Tracking.** A sister tracks the whole catalog unless its `catalog.py`
  narrows it with `commodities(tracked=[...])`. Nothing else to add: the
  sources fetch what the catalog lists.
- **Market facts, in the sister's seeds.** The unit the local market quotes in
  (`market_units`; same dimension as the quote unit or the unit test fails), a duty row valid from a date (a change is a new
  dated row and the old row only has its interval closed, ADR-0001), an
  exchange contract's quote basis and lot only if one trades it
  (`mcx_contract_lots` in India, `us_contract_lots` in the US), purities only
  for retail precious metals. Read the
  sister's `transform/seeds/_seeds.yml` for the columns and tests; never copy
  another market's values.
- **Seed and read back.** `pf seed commodity <sister>` lands the raw datasets,
  writes the annotations, builds dbt and rebuilds the graph and the card. Then
  read the card's **Known gaps** (a raw table reaching no metric is the usual
  one) and run `pf check`. The singular tests
  `assert_every_commodity_is_priced` and
  `assert_every_commodity_has_a_tariff_today` are what catch a half-added
  commodity.
