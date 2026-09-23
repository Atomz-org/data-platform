---
type: Relation
title: payment_reversed_by_refund
description: Payment reversed by Refund
okf_x_tier: platform
okf_x_domain: Payment
okf_x_range: Refund
okf_x_cardinality: ONE_TO_MANY
okf_x_inverse: reverses
---

# Reading it

* Payment reversed by Refund
* Reverse: Refund reverses Payment

# Between

* Domain: [Payment](/concepts/Payment.md)
* Range: [Refund](/concepts/Refund.md)
