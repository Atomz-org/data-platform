---
type: Concept
title: Commodity
description: A traded raw material with an international benchmark, quoted per a physical
  unit.
okf_x_defined_in: group
okf_x_parent: Product
okf_x_identity: commodity_id
---

Declared in `groups/commodity/ontology/extension.yaml`, shared by every sister of `commodity`.

# Instantiated by

* [dim_commodities](/tables/dim_commodities.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `category` | string | status_enum |
| `commodity_id` | string | natural_key |
| `commodity_name` | string | free_text |
| `quote_unit` | string | unit_of_measure |
| `segment` | string | status_enum |

# Relations

* ImportTariff is levied on Commodity — A tariff row applies to one commodity for one validity interval.
* Order contains Product — Needs a line-item bridge in any physical model.
* PriceObservation prices Commodity — Every benchmark price belongs to exactly one commodity.
* Subscription for product Product — 
