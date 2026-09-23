---
type: Concept
title: PriceObservation
description: One benchmark price for one commodity at one point in time. Never summed.
okf_x_tier: group
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: quote_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `close_price` | decimal | [unit_price](/roles/unit_price.md) |
| `commodity_id` | string | [foreign_key](/roles/foreign_key.md) |
| `currency_code` | string | [currency_code](/roles/currency_code.md) |
| `quote_id` | string | [natural_key](/roles/natural_key.md) |
| `traded_at` | timestamp | [event_time](/roles/event_time.md) |
| `volume` | integer | [quantity](/roles/quantity.md) |

# Relations

* [price_observation_in_market](/relations/price_observation_in_market.md) — PriceObservation is landed in Market
* [price_observation_of_commodity](/relations/price_observation_of_commodity.md) — PriceObservation prices Commodity
