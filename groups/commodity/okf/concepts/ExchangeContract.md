---
type: Concept
title: ExchangeContract
description: A standardised exchange-traded derivative on one commodity — a futures
  contract, or one expiry's chain of options — identified by exchange, instrument,
  contract code and expiry.
okf_x_tier: group
okf_x_parent: Product
okf_x_abstract: false
okf_x_identity: contract_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `commodity_id` | string | [foreign_key](/roles/foreign_key.md) |
| `contract_code` | string | [free_text](/roles/free_text.md) |
| `contract_id` | string | [natural_key](/roles/natural_key.md) |
| `expiry_date` | date | [reference_date](/roles/reference_date.md) |
| `instrument_type` | string | [status_enum](/roles/status_enum.md) |
| `is_traded_today` | boolean | [flag](/roles/flag.md) |

# Relations

* [contract_session_of_exchange_contract](/relations/contract_session_of_exchange_contract.md) — ContractSession settles ExchangeContract
* [exchange_contract_listed_in_market](/relations/exchange_contract_listed_in_market.md) — ExchangeContract is listed in Market
* [exchange_contract_on_commodity](/relations/exchange_contract_on_commodity.md) — ExchangeContract is written on Commodity
* [order_contains_product](/relations/order_contains_product.md) — Order contains Product
* [subscription_for_product](/relations/subscription_for_product.md) — Subscription for product Product
