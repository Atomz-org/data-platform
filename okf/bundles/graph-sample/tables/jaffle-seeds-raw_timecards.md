---
type: Table
title: raw_timecards
description: Induced from raw_timecards by `pf semantic scan`.
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
| `work_date` | ? | event_time |
| `clock_in` | ? | event_time |
| `clock_out` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Timecard`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
