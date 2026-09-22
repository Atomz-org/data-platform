---
type: Concept
title: Subscription
description: A recurring agreement with a plan, term and status.
okf_x_tier: platform
okf_x_parent: Agreement
okf_x_abstract: false
okf_x_identity: subscription_id
---

# Properties

| Property | Datatype | Role |
|---|---|---|
| `canceled_at` | timestamp | [valid_to](/roles/valid_to.md) |
| `currency` | string | [currency_code](/roles/currency_code.md) |
| `mrr_amount` | decimal | [money_amount](/roles/money_amount.md) |
| `plan` | string | [status_enum](/roles/status_enum.md) |
| `started_at` | timestamp | [event_time](/roles/event_time.md) |
| `status` | string | [status_enum](/roles/status_enum.md) |
| `subscription_id` | string | [natural_key](/roles/natural_key.md) |

# Relations

* [customer_holds_subscription](/relations/customer_holds_subscription.md) — Customer holds Subscription
* [subscription_for_product](/relations/subscription_for_product.md) — Subscription for product Product
* [subscription_metered_by_usage](/relations/subscription_metered_by_usage.md) — Subscription metered by Usage
* [subscription_settled_by_payment](/relations/subscription_settled_by_payment.md) — Subscription settled by Payment
