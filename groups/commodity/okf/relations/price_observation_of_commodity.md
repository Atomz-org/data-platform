---
type: Relation
title: price_observation_of_commodity
description: Every benchmark price belongs to exactly one commodity.
okf_x_tier: group
okf_x_domain: PriceObservation
okf_x_range: Commodity
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: is priced by
---

# Reading it

* PriceObservation prices Commodity
* Reverse: Commodity is priced by PriceObservation

# Between

* Domain: [PriceObservation](/concepts/PriceObservation.md)
* Range: [Commodity](/concepts/Commodity.md)
