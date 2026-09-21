---
type: Table
title: raw_performance_reviews
description: Induced from raw_performance_reviews by `pf semantic scan`.
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
| `reviewer_id` | ? | foreign_key |
| `review_date` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:PerformanceReview`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
