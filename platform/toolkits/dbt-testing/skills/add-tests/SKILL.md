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

## The wider vocabulary

The `expectations` tool installs **dbt-expectations** project-wide, so any
model yml can use its Great Expectations-style tests directly
(`dbt_expectations.expect_column_values_to_be_between`, `..._to_be_in_set`,
`..._to_match_regex`, ...). Reach for it when the assertion outgrows dbt's
four built-ins — ranges, sets, regexes, row-count shapes — and see
`docs/expectations.md` in the project for the worked form.

Two kinds of coverage are not yours to write:

- `transform/tests/expectations/` is the **generated floor** — derived from
  the ontology roles by `pf bootstrap`. Fix the role, never the file.
- A rule that cannot be written down (volumes, freshness, drift) is a
  **monitor**, not a test: `elementary-observe: add-anomaly-tests`.
