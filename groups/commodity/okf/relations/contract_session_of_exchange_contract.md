---
type: Relation
title: contract_session_of_exchange_contract
description: Every trading day an exchange reports belongs to exactly one contract
  (for options, one expiry's chain).
okf_x_tier: group
okf_x_domain: ContractSession
okf_x_range: ExchangeContract
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: is settled by
---

# Reading it

* ContractSession settles ExchangeContract
* Reverse: ExchangeContract is settled by ContractSession

# Between

* Domain: [ContractSession](/concepts/ContractSession.md)
* Range: [ExchangeContract](/concepts/ExchangeContract.md)
