---
type: Concept
title: Market
description: A jurisdiction commodities are landed in — one sister project, one currency,
  one customs regime. The tenant of this family.
okf_x_tier: group
okf_x_parent: Location
okf_x_abstract: false
okf_x_identity: market_code
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country_code` | string | [geo_country](/roles/geo_country.md) |
| `currency_code` | string | [currency_code](/roles/currency_code.md) |
| `market_code` | string | [natural_key](/roles/natural_key.md) |

# Relations

* [customer_located_in_location](/relations/customer_located_in_location.md) — Customer located in Location
* [price_observation_in_market](/relations/price_observation_in_market.md) — PriceObservation is landed in Market
