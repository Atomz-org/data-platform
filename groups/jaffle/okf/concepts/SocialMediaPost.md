---
type: Concept
title: SocialMediaPost
description: Induced from `raw_social_media_posts` and approved by onboarding-ladder.
okf_x_tier: group
okf_x_parent: null
okf_x_abstract: false
okf_x_identity: id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `campaign_id` | integer | [foreign_key](/roles/foreign_key.md) |
| `id` | integer | [natural_key](/roles/natural_key.md) |
| `posted_at` | timestamp | [event_time](/roles/event_time.md) |
