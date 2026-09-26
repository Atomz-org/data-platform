---
type: Concept
title: Commodity
description: A traded raw material with an international benchmark, quoted per a physical
  unit.
okf_x_defined_in: group
okf_x_parent: Product
okf_x_identity: commodity_id
okf_x_kg_node: concept:Commodity
okf_x_group_concept: ../../../../okf/concepts/Commodity.md
---

Declared by this family: [Commodity](../../../../okf/concepts/Commodity.md) in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [dim_commodities](/tables/dim_commodities.md)
* [rpt_commodity_price_board](/tables/rpt_commodity_price_board.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `category` | string | status_enum |
| `commodity_id` | string | natural_key |
| `commodity_name` | string | free_text |
| `quote_unit` | string | unit_of_measure |
| `segment` | string | status_enum |

# Relations

* ExchangeContract is written on Commodity — A contract's underlying. Optional — an exchange lists contracts (electricity, cardamom) the family catalogue does not price.
* ImportTariff is levied on Commodity — A tariff row applies to one commodity for one validity interval.
* Order contains Product — Needs a line-item bridge in any physical model.
* PriceObservation prices Commodity — Every benchmark price belongs to exactly one commodity.
* Subscription for product Product — 

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
