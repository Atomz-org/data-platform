---
type: Table
title: raw_payroll
description: Induced from raw_payroll by `pf semantic scan`.
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
| `pay_period_start` | ? | event_time |
| `pay_period_end` | ? | event_time |
| `pay_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Payroll`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
