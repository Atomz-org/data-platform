---
type: Table
title: raw_referrals
description: Induced from raw_referrals by `pf semantic scan`.
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
| `referrer_customer_id` | ? | foreign_key |
| `referee_customer_id` | ? | foreign_key |
| `campaign_id` | ? | foreign_key |
| `reward_amount` | ? | money_amount |
| `referred_at` | ? | event_time |
| `converted_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:Referral`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
