---
type: Concept
title: ContractSession
description: One exchange contract's trading day as the exchange settles it — open,
  high, low, close, the previous settlement, volume and open interest in lots, and
  turnover. Prices are per the contract's quote basis and never summed; volume and
  turnover are additive within a day.
okf_x_defined_in: group
okf_x_parent: Event
okf_x_identity: session_id
okf_x_kg_node: concept:ContractSession
okf_x_group_concept: ../../../../okf/concepts/ContractSession.md
---

Declared by this family: [ContractSession](../../../../okf/concepts/ContractSession.md) in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [fct_mcx_commodity_daily](/tables/fct_mcx_commodity_daily.md)
* [fct_mcx_futures_daily](/tables/fct_mcx_futures_daily.md)
* [fct_mcx_options_daily](/tables/fct_mcx_options_daily.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `close_price` | decimal | unit_price |
| `contract_id` | string | foreign_key |
| `open_interest_lots` | integer | quantity |
| `session_id` | string | natural_key |
| `traded_at` | timestamp | event_time |
| `turnover_lakhs` | decimal | money_amount |
| `volume_lots` | integer | quantity |

# Relations

* ContractSession settles ExchangeContract — Every trading day an exchange reports belongs to exactly one contract (for options, one expiry's chain).

# Raw tables that instantiate it

* `mcx.futures_bhavcopy`
* `mcx.options_bhavcopy`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
* **Decision** ADR-0006 — MCX's own bhavcopy lands as one dlt pipeline per commodity (accepted)
