---
type: Table
title: raw_training_completions
description: Induced from raw_training_completions by `pf semantic scan`.
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
| `course_id` | ? | foreign_key |
| `started_at` | ? | event_time |
| `completed_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:TrainingCompletion`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
