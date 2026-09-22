---
type: Concept
title: Commodity
description: A traded raw material with an international benchmark, quoted per a physical
  unit.
okf_x_tier: group
okf_x_parent: Product
okf_x_abstract: false
okf_x_identity: commodity_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `category` | string | [status_enum](/roles/status_enum.md) |
| `commodity_id` | string | [natural_key](/roles/natural_key.md) |
| `commodity_name` | string | [free_text](/roles/free_text.md) |
| `quote_unit` | string | [unit_of_measure](/roles/unit_of_measure.md) |
| `segment` | string | [status_enum](/roles/status_enum.md) |

# Relations

* [import_tariff_on_commodity](/relations/import_tariff_on_commodity.md) — ImportTariff is levied on Commodity
* [order_contains_product](/relations/order_contains_product.md) — Order contains Product
* [price_observation_of_commodity](/relations/price_observation_of_commodity.md) — PriceObservation prices Commodity
* [subscription_for_product](/relations/subscription_for_product.md) — Subscription for product Product
