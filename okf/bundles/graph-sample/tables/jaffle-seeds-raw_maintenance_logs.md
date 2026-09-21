---
type: Table
title: raw_maintenance_logs
description: Induced from raw_maintenance_logs by `pf semantic scan`.
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
| `equipment_id` | ? | foreign_key |
| `cost` | ? | money_amount |
| `scheduled_date` | ? | event_time |
| `completed_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:MaintenanceLog`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
