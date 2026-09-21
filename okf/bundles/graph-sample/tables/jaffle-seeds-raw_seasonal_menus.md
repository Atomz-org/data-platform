---
type: Table
title: raw_seasonal_menus
description: Induced from raw_seasonal_menus by `pf semantic scan`.
tags:
- jaffle-shop
- raw
- graph-sample
status: stable
---

# Schema

| Column | Type | Role |
|---|---|---|
| `id` | ? | natural_key |
| `menu_item_id` | ? | foreign_key |
| `start_date` | ? | event_time |
| `end_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:SeasonalMenu`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
