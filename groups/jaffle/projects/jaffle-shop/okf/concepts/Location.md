---
type: Concept
title: Location
description: A geography. Country, region, or address.
okf_x_defined_in: platform
okf_x_parent: null
okf_x_identity: location_id
okf_x_kg_node: concept:Location
okf_x_platform_concept: ../../../../../../platform/okf/concepts/Location.md
---

Defined by the platform ontology: [Location](../../../../../../platform/okf/concepts/Location.md).

# Instantiated by

* [locations](/tables/locations.md)
* [met_weekly_revenue_by_store](/tables/met_weekly_revenue_by_store.md)
* [rev_etl_inventory_reorder](/tables/rev_etl_inventory_reorder.md)
* [rpt_store_pnl](/tables/rpt_store_pnl.md)
* [view_store_mgr_daily_report](/tables/view_store_mgr_daily_report.md)
* [view_store_mgr_inventory_status](/tables/view_store_mgr_inventory_status.md)

# Properties

| Property | Datatype | Role |
|---|---|---|
| `country` | string | geo_country |
| `location_id` | string | natural_key |

# Relations

* Customer located in Location — 

# Governance

* **Policy** `entity-requires-identity` (error) — A class with no identity property cannot participate in a derived join, so every BI and MDL projection of it is a guess.
