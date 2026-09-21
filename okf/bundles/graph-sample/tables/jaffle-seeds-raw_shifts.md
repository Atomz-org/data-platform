---
type: Table
title: raw_shifts
description: Induced from raw_shifts by `pf semantic scan`.
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
| `employee_id` | ? | foreign_key |
| `store_id` | ? | foreign_key |
| `shift_date` | ? | event_time |
| `scheduled_start` | ? | event_time |
| `scheduled_end` | ? | event_time |
| `actual_start` | ? | event_time |
| `actual_end` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Shift`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
