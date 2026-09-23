---
type: Role
title: money_amount
description: Monetary value. Requires a sibling currency_code.
okf_x_tier: platform
okf_x_datatype: decimal
okf_x_pii: false
okf_x_review: null
---

# Policies

* `money-amount-bounded` — A monetary column with no lower bound accepts the negative row that a refund, a sign flip or a bad join produces, and it reaches a metric as a quietly smaller number. The currency rule makes the amount interpretable; this makes it credible.
* `money-requires-currency` — A monetary amount without its currency is not a number, it is a bug waiting for a second entity to be onboarded.
