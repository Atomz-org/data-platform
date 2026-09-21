---
type: Table
title: raw_campaign_spend
description: Induced from raw_campaign_spend by `pf semantic scan`.
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
| `amount` | ? | money_amount |
| `spend_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:CampaignSpend`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
