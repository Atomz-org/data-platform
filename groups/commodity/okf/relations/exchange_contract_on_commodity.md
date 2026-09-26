---
type: Relation
title: exchange_contract_on_commodity
description: A contract's underlying. Optional — an exchange lists contracts (electricity,
  cardamom) the family catalogue does not price.
okf_x_tier: group
okf_x_domain: ExchangeContract
okf_x_range: Commodity
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: underlies
---

# Reading it

* ExchangeContract is written on Commodity
* Reverse: Commodity underlies ExchangeContract

# Between

* Domain: [ExchangeContract](/concepts/ExchangeContract.md)
* Range: [Commodity](/concepts/Commodity.md)
