---
type: Table
title: raw_email_events
description: Induced from raw_email_events by `pf semantic scan`.
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
| `campaign_id` | ? | foreign_key |
| `customer_id` | ? | foreign_key |
| `event_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:EmailEvent`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
