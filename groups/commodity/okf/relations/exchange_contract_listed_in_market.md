---
type: Relation
title: exchange_contract_listed_in_market
description: The market whose exchange lists the contract; its prices are in that
  market's currency.
okf_x_tier: group
okf_x_domain: ExchangeContract
okf_x_range: Market
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: lists
---

# Reading it

* ExchangeContract is listed in Market
* Reverse: Market lists ExchangeContract

# Between

* Domain: [ExchangeContract](/concepts/ExchangeContract.md)
* Range: [Market](/concepts/Market.md)
