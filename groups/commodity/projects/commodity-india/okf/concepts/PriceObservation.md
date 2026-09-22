---
type: Concept
title: PriceObservation
description: One benchmark price for one commodity at one point in time. Never summed.
okf_x_defined_in: group
okf_x_parent: Event
okf_x_identity: quote_id
okf_x_kg_node: concept:PriceObservation
okf_x_group_concept: ../../../../okf/concepts/PriceObservation.md
---

Declared by this family: [PriceObservation](../../../../okf/concepts/PriceObservation.md) in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [fct_commodity_prices_daily](/tables/fct_commodity_prices_daily.md)
* [fct_landed_prices_daily](/tables/fct_landed_prices_daily.md)
* [fct_mcx_lot_equivalents_daily](/tables/fct_mcx_lot_equivalents_daily.md)
* [fct_precious_metal_retail_prices_daily](/tables/fct_precious_metal_retail_prices_daily.md)
* [rpt_mcx_contract_board](/tables/rpt_mcx_contract_board.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `close_price` | decimal | unit_price |
| `commodity_id` | string | foreign_key |
| `currency_code` | string | currency_code |
| `quote_id` | string | natural_key |
| `traded_at` | timestamp | event_time |
| `volume` | integer | quantity |

# Relations

* PriceObservation is landed in Market — A landed price is one market's price; the benchmark it derives from belongs to none.
* PriceObservation prices Commodity — Every benchmark price belongs to exactly one commodity.

# Raw tables that instantiate it

* `yahoo_finance.futures_prices`
* `gold_api.spot_prices`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
