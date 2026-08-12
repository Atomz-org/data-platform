---
name: add-tests
description: Add generic and singular data tests to a model.
---
# Data tests

Generate from annotations rather than by hand — roles already declare intent:

| Role | Test |
|---|---|
| `natural_key` / `surrogate_key` | `unique`, `not_null` |
| `foreign_key` | `relationships` to the linked model |
| `status_enum` | `accepted_values` |
| `money_amount` | `not_null`, plus a non-negative singular test where applicable |
| `event_time` | `not_null`, freshness at source |

Put severity deliberately: `error` on key and referential tests, `warn` on
distribution ones. A test that always warns and is never fixed is noise — delete
it or promote it to a monitor.
