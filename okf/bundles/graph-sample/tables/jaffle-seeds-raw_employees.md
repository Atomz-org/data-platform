---
type: Table
title: raw_employees
description: Induced from raw_employees by `pf semantic scan`.
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
| `department_id` | ? | foreign_key |
| `position_id` | ? | foreign_key |
| `hire_date` | ? | event_time |
| `termination_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Employee`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
