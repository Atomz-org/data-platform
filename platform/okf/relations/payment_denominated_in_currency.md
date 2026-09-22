---
type: Relation
title: payment_denominated_in_currency
description: Makes the money/currency pairing explicit rather than a convention.
okf_x_tier: platform
okf_x_domain: Payment
okf_x_range: Currency
okf_x_cardinality: MANY_TO_ONE
okf_x_inverse: denominates
---

# Reading it

* Payment denominated in Currency
* Reverse: Currency denominates Payment

# Between

* Domain: [Payment](/concepts/Payment.md)
* Range: [Currency](/concepts/Currency.md)
