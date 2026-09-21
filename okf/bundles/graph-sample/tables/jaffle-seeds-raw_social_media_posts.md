---
type: Table
title: raw_social_media_posts
description: Induced from raw_social_media_posts by `pf semantic scan`.
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
| `posted_at` | ? | event_time |

# Provenance

Instantiates ontology concept `concept:SocialMediaPost`. Sourced from [source:jaffle-seeds](/sources/jaffle-seeds.md).
