---
type: Concept
title: ContractSession
description: One exchange contract's trading day as the exchange settles it — open,
  high, low, close, the previous settlement, volume and open interest in lots, and
  turnover. Prices are per the contract's quote basis and never summed; volume and
  turnover are additive within a day.
okf_x_tier: group
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: session_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `close_price` | decimal | [unit_price](/roles/unit_price.md) |
| `contract_id` | string | [foreign_key](/roles/foreign_key.md) |
| `open_interest_lots` | integer | [quantity](/roles/quantity.md) |
| `session_id` | string | [natural_key](/roles/natural_key.md) |
| `traded_at` | timestamp | [event_time](/roles/event_time.md) |
| `turnover_lakhs` | decimal | [money_amount](/roles/money_amount.md) |
| `volume_lots` | integer | [quantity](/roles/quantity.md) |

# Relations

* [contract_session_of_exchange_contract](/relations/contract_session_of_exchange_contract.md) — ContractSession settles ExchangeContract
