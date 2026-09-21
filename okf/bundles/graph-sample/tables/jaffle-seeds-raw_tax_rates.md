---
type: Table
title: raw_tax_rates
description: Induced from raw_tax_rates by `pf semantic scan`.
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
| `effective_from` | ? | event_time |
| `effective_to` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:TaxRate`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
