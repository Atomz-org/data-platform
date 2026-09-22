---
type: Relation
title: import_tariff_on_commodity
description: A tariff row applies to one commodity for one validity interval.
okf_x_tier: group
okf_x_domain: ImportTariff
okf_x_range: Commodity
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: is subject to
---

# Reading it

* ImportTariff is levied on Commodity
* Reverse: Commodity is subject to ImportTariff

# Between

* Domain: [ImportTariff](/concepts/ImportTariff.md)
* Range: [Commodity](/concepts/Commodity.md)
