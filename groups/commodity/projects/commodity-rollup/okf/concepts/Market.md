---
type: Concept
title: Market
description: A jurisdiction commodities are landed in — one sister project, one currency,
  one customs regime. The tenant of this family.
okf_x_defined_in: group
okf_x_parent: Location
okf_x_identity: market_code
---

Declared in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [dim_markets](/tables/dim_markets.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country_code` | string | geo_country |
| `currency_code` | string | currency_code |
| `market_code` | string | natural_key |

# Relations

* Customer located in Location — 
* PriceObservation is landed in Market — A landed price is one market's price; the benchmark it derives from belongs to none.
