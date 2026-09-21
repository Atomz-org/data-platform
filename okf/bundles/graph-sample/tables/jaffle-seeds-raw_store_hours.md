---
type: Table
title: raw_store_hours
description: Induced from raw_store_hours by `pf semantic scan`.
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
| `store_id` | ? | foreign_key |

# Provenance

Instantiates ontology concept `concept:StoreHour`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
