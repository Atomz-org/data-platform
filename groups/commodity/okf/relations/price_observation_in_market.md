---
type: Relation
title: price_observation_in_market
description: A landed price is one market's price; the benchmark it derives from belongs
  to none.
okf_x_tier: group
okf_x_domain: PriceObservation
okf_x_range: Market
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: lands
---

# Reading it

* PriceObservation is landed in Market
* Reverse: Market lands PriceObservation

# Between

* Domain: [PriceObservation](/concepts/PriceObservation.md)
* Range: [Market](/concepts/Market.md)
