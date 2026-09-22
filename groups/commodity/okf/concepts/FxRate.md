---
type: Concept
title: FxRate
description: A daily exchange-rate fix — units of quote currency per one unit of base
  currency.
okf_x_tier: group
okf_x_parent: Event
okf_x_abstract: false
okf_x_identity: fx_rate_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `base_currency_code` | string | [currency_code](/roles/currency_code.md) |
| `fx_rate_id` | string | [natural_key](/roles/natural_key.md) |
| `quote_currency_code` | string | [currency_code](/roles/currency_code.md) |
| `rate` | decimal | [exchange_rate](/roles/exchange_rate.md) |
| `rate_at` | timestamp | [event_time](/roles/event_time.md) |
