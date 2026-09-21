---
type: Table
title: raw_invoice_line_items
description: Induced from raw_invoice_line_items by `pf semantic scan`.
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
| `invoice_id` | ? | foreign_key |
| `product_id` | ? | foreign_key |
| `unit_price` | ? | money_amount |
| `line_total` | ? | money_amount |

# Provenance

Instantiates ontology concept `concept:InvoiceLineItem`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
