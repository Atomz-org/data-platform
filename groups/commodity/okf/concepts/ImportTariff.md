---
type: Concept
title: ImportTariff
description: Customs duty a jurisdiction levies on importing a commodity, valid over
  an interval.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: tariff_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `commodity_id` | string | [foreign_key](/roles/foreign_key.md) |
| `effective_duty_rate` | decimal | [rate_fraction](/roles/rate_fraction.md) |
| `market_country` | string | [geo_country](/roles/geo_country.md) |
| `tariff_id` | string | [natural_key](/roles/natural_key.md) |
| `valid_from` | timestamp | [valid_from](/roles/valid_from.md) |
| `valid_to` | timestamp | [valid_to](/roles/valid_to.md) |

# Relations

* [import_tariff_on_commodity](/relations/import_tariff_on_commodity.md) — ImportTariff is levied on Commodity
