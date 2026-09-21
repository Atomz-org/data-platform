---
type: Table
title: raw_accounts_receivable
description: Induced from raw_accounts_receivable by `pf semantic scan`.
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
| `customer_id` | ? | foreign_key |
| `invoice_id` | ? | foreign_key |
| `amount_due` | ? | money_amount |
| `amount_paid` | ? | money_amount |
| `amount_outstanding` | ? | money_amount |
| `due_at` | ? | event_time |
| `created_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:AccountReceivable`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
