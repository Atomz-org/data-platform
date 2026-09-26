---
type: Concept
title: ExchangeContract
description: A standardised exchange-traded derivative on one commodity — a futures
  contract, or one expiry's chain of options — identified by exchange, instrument,
  contract code and expiry.
okf_x_defined_in: group
okf_x_parent: Product
okf_x_identity: contract_id
okf_x_kg_node: concept:ExchangeContract
okf_x_group_concept: ../../../../okf/concepts/ExchangeContract.md
---

Declared by this family: [ExchangeContract](../../../../okf/concepts/ExchangeContract.md) in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [dim_mcx_contracts](/tables/dim_mcx_contracts.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `commodity_id` | string | foreign_key |
| `contract_code` | string | free_text |
| `contract_id` | string | natural_key |
| `expiry_date` | date | reference_date |
| `instrument_type` | string | status_enum |
| `is_traded_today` | boolean | flag |

# Relations

* ContractSession settles ExchangeContract — Every trading day an exchange reports belongs to exactly one contract (for options, one expiry's chain).
* ExchangeContract is listed in Market — The market whose exchange lists the contract; its prices are in that market's currency.
* ExchangeContract is written on Commodity — A contract's underlying. Optional — an exchange lists contracts (electricity, cardamom) the family catalogue does not price.
* Order contains Product — Needs a line-item bridge in any physical model.
* Subscription for product Product — 

# Raw tables that instantiate it

* `mcx.contract_master`

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
* **Decision** ADR-0006 — MCX's own bhavcopy lands as one dlt pipeline per commodity (accepted)
